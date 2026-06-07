"""赛博财神爷 Agent 核心：意图识别 -> 比价 -> 目标进度 -> 冲动指数 -> 裁决 -> 人格化文案。

输出包含可见的 CoT 推理步骤、量化冲动指数与机会成本，便于前端展示"逻辑链"。
支持多轮上下文（追问复用上一笔消费）与历史会话喂给 LLM。
"""
from __future__ import annotations

from typing import Optional

from . import goal_service, intent as intent_mod, llm, price_db, prompts
from .models import (
    ChatContext,
    ChatResponse,
    ChatTurn,
    CotStep,
    GoalImpact,
    ImpulseScore,
    PriceInfo,
    Verdict,
)


def decide_verdict(price: Optional[PriceInfo], impact: GoalImpact) -> Verdict:
    """基于溢价率、消费占目标比例、延后天数做规则裁决。"""
    if price is None or price.user_price is None:
        return "neutral"
    overprice = price.overprice_ratio if price.overprice_ratio is not None else 0.0
    impact_ratio = impact.goal_impact_ratio or 0.0
    delay = impact.delay_days or 0

    if overprice >= 1.0 or impact_ratio >= 0.10 or delay >= 30:
        return "discourage"
    if overprice <= 0.3 and impact_ratio <= 0.03 and delay <= 7:
        return "encourage"
    return "neutral"


def compute_impulse(price: Optional[PriceInfo], impact: Optional[GoalImpact]) -> Optional[ImpulseScore]:
    """计算冲动指数（0-100）：溢价率 0.45 + 占目标比例 0.35 + 延后天数 0.20。"""
    if price is None or price.user_price is None:
        return None
    overprice = max(price.overprice_ratio or 0.0, 0.0)
    impact_ratio = (impact.goal_impact_ratio or 0.0) if impact else 0.0
    delay = (impact.delay_days or 0) if impact else 0

    s_over = min(overprice, 2.0) / 2.0
    s_impact = min(impact_ratio, 0.3) / 0.3
    s_delay = min(delay, 60) / 60
    score = int(round((0.45 * s_over + 0.35 * s_impact + 0.20 * s_delay) * 100))

    reasons: list[str] = []
    if overprice > 0.5:
        reasons.append(f"溢价 {overprice * 100:.0f}%")
    if impact_ratio > 0.05:
        reasons.append(f"占攒钱目标 {impact_ratio * 100:.1f}%")
    if delay >= 7:
        reasons.append(f"目标延后约 {delay} 天")
    if not reasons:
        reasons.append("价格合理、对目标影响很小")

    if score < 30:
        level = "理智"
    elif score < 55:
        level = "有点犹豫"
    elif score < 80:
        level = "冲动"
    else:
        level = "剁手警告"
    return ImpulseScore(score=score, level=level, reasons=reasons)


def _build_cot(intent_res, price, impact, impulse, oc, verdict) -> list[CotStep]:
    steps: list[CotStep] = []
    detail = f"意图：{intent_res.intent}"
    if intent_res.item:
        detail += f"｜物品：{intent_res.item}"
    if intent_res.price is not None:
        detail += f"｜金额：¥{intent_res.price:.0f}"
    steps.append(CotStep(label="意图识别", detail=detail))

    if price:
        c = price.comment
        if price.save_if_lowest:
            c += f" 买到底价可省 ¥{price.save_if_lowest:.0f}。"
        steps.append(CotStep(label="模拟比价", detail=c))

    if impact:
        steps.append(CotStep(label="攒钱目标进度", detail=impact.note))

    if oc:
        steps.append(CotStep(label="机会成本", detail="这笔钱 " + "，".join(oc) + "。"))

    if impulse:
        steps.append(CotStep(label="冲动指数", detail=f"{impulse.score}/100（{impulse.level}）— " + "、".join(impulse.reasons)))

    if verdict:
        verdict_cn = {"discourage": "劝退 🛑", "encourage": "鼓励 ✅", "neutral": "理性提醒 ⚖️"}[verdict]
        steps.append(CotStep(label="财神裁决", detail=verdict_cn))
    return steps


def handle_chat(
    message: str,
    role: str,
    history: Optional[list[ChatTurn]] = None,
    context: Optional[ChatContext] = None,
    db_path: Optional[str] = None,
) -> ChatResponse:
    intent_res = intent_mod.recognize(message, context)
    goal = goal_service.get_current_goal(db_path)

    # 克制 / 决定不买：给予正反馈，并引导把省下的钱存进目标
    if intent_res.intent == "resist":
        impact = GoalImpact(has_goal=goal is not None, note=_resist_note(goal, intent_res.price))
        reply, used = _persona_text(role, message, None, impact, None, history)
        ctx = ChatContext(last_item=intent_res.item, last_price=intent_res.price)
        return ChatResponse(
            reply=reply, role=role, intent="resist", impact=impact,
            cot_steps=_build_cot(intent_res, None, impact, None, [], None),
            context=ctx, llm_used=used,
        )

    if intent_res.intent == "set_goal":
        impact = GoalImpact(has_goal=goal is not None, note=_goal_hint(goal, intent_res.target_amount))
        reply, used = _persona_text(role, message, None, impact, None, history)
        return ChatResponse(
            reply=reply, role=role, intent="set_goal", impact=impact,
            cot_steps=_build_cot(intent_res, None, impact, None, [], None), llm_used=used,
        )

    if intent_res.intent == "query_progress":
        progress = goal_service.compute_progress(goal)
        impact = GoalImpact(has_goal=goal is not None, note=_progress_note(progress))
        reply, used = _persona_text(role, message, None, impact, None, history)
        return ChatResponse(
            reply=reply, role=role, intent="query_progress", impact=impact,
            cot_steps=_build_cot(intent_res, None, impact, None, [], None), llm_used=used,
        )

    if intent_res.intent == "chitchat":
        impact = GoalImpact(has_goal=goal is not None, note=_goal_hint(goal, None))
        reply, used = _persona_text(role, message, None, impact, None, history)
        return ChatResponse(
            reply=reply, role=role, intent="chitchat",
            cot_steps=_build_cot(intent_res, None, impact, None, [], None), llm_used=used,
        )

    # 消费意图：完整推理链
    price = price_db.lookup(intent_res.item, intent_res.price, message)
    impact = goal_service.compute_impact(goal, intent_res.price)
    impulse = compute_impulse(price, impact)
    oc = price_db.opportunity_cost(intent_res.price)
    verdict = decide_verdict(price, impact)
    reply, used = _persona_text(role, message, price, impact, verdict, history, impulse, oc)
    ctx = ChatContext(last_item=intent_res.item or price.item, last_price=intent_res.price)

    return ChatResponse(
        reply=reply,
        role=role,
        intent="purchase",
        verdict=verdict,
        price=price,
        impact=impact,
        impulse=impulse,
        opportunity_cost=oc,
        cot_steps=_build_cot(intent_res, price, impact, impulse, oc, verdict),
        context=ctx,
        llm_used=used,
    )


def _persona_text(role, message, price, impact, verdict, history, impulse=None, oc=None) -> tuple[str, bool]:
    """优先 LLM（含多轮历史），失败回退本地模板。返回 (文本, 是否用了LLM)。"""
    system = prompts.system_prompt(role)
    user_ctx = prompts.build_user_context(message, price, impact, verdict, impulse, oc)
    text = llm.chat(system, user_ctx, history=history)
    if text:
        return text, True
    return prompts.fallback_reply(role, message, price, impact, verdict), False


def _goal_hint(goal, mentioned_amount) -> str:
    if not goal:
        if mentioned_amount:
            return f"想攒 ¥{mentioned_amount:.0f} 是吧？在左边面板把目标名称填上、点保存，我就帮你盯着钱包啦～"
        return "你还没设定攒钱目标，左边面板设一个吧，我好帮你盯着钱包～"
    return f"你的攒钱目标「{goal.name}」，目标 ¥{goal.target_amount:.0f}，已攒 ¥{goal.saved_amount:.0f}。"


def _resist_note(goal, price) -> str:
    base = "你主动管住了手，这波很可以！"
    if price and goal:
        return base + f" 把这省下的 ¥{price:.0f} 存进「{goal.name}」，离目标又近一步。"
    if price:
        return base + f" 省下的 ¥{price:.0f} 建议直接存起来。"
    return base + " 省下的钱记得存进攒钱目标哦。"


def _progress_note(progress) -> str:
    if not progress.goal:
        return "还没设定攒钱目标哦，先定个小目标吧～"
    g = progress.goal
    note = f"目标「{g.name}」：已攒 ¥{g.saved_amount:.0f} / ¥{g.target_amount:.0f}，进度 {progress.progress_ratio*100:.1f}%，还差 ¥{progress.remaining:.0f}。"
    if progress.months_to_go is not None:
        note += f"按当前速度约还需 {progress.months_to_go} 个月。"
    return note
