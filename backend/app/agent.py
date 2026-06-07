"""赛博财神爷 Agent 核心：意图识别 -> 比价 -> 目标进度 -> 裁决 -> 人格化文案。

输出包含可见的 CoT 推理步骤，便于前端展示"逻辑链"。
"""
from __future__ import annotations

from typing import Optional

from . import goal_service, intent as intent_mod, llm, price_db, prompts
from .models import (
    ChatResponse,
    CotStep,
    GoalImpact,
    PriceInfo,
    Verdict,
)


def decide_verdict(price: Optional[PriceInfo], impact: GoalImpact) -> Verdict:
    """基于溢价率、消费占目标比例、延后天数做规则裁决。"""
    # 没识别到具体价格时，不轻率鼓励，统一给"理性提醒"
    if price is None or price.user_price is None:
        return "neutral"
    overprice = price.overprice_ratio if price and price.overprice_ratio is not None else 0.0
    impact_ratio = impact.goal_impact_ratio or 0.0
    delay = impact.delay_days or 0

    # 强劝退信号
    if overprice >= 1.0 or impact_ratio >= 0.10 or delay >= 30:
        return "discourage"
    # 鼓励信号：价格划算且占比很低
    if overprice <= 0.3 and impact_ratio <= 0.03 and delay <= 7:
        return "encourage"
    return "neutral"


def _build_cot(intent_res, price: Optional[PriceInfo], impact: GoalImpact, verdict: Optional[Verdict]) -> list[CotStep]:
    steps: list[CotStep] = []
    # 1. 意图识别
    detail = f"意图：{intent_res.intent}"
    if intent_res.item:
        detail += f"｜物品：{intent_res.item}"
    if intent_res.price is not None:
        detail += f"｜金额：¥{intent_res.price:.0f}"
    steps.append(CotStep(label="意图识别", detail=detail))

    # 2. 比价
    if price:
        steps.append(CotStep(label="模拟比价", detail=price.comment))

    # 3. 目标影响
    if impact:
        steps.append(CotStep(label="攒钱目标进度", detail=impact.note))

    # 4. 裁决
    if verdict:
        verdict_cn = {"discourage": "劝退 🛑", "encourage": "鼓励 ✅", "neutral": "理性提醒 ⚖️"}[verdict]
        steps.append(CotStep(label="财神裁决", detail=verdict_cn))
    return steps


def handle_chat(message: str, role: str, db_path: Optional[str] = None) -> ChatResponse:
    intent_res = intent_mod.recognize(message)
    goal = goal_service.get_current_goal(db_path)

    # 设定目标意图：聊天侧只做人格化引导，真正创建目标走左侧面板 / POST /api/goal
    if intent_res.intent == "set_goal":
        impact = GoalImpact(has_goal=goal is not None, note=_goal_hint(goal))
        reply, used = _persona_text(role, message, None, impact, None)
        return ChatResponse(
            reply=reply, role=role, intent="set_goal", impact=impact,
            cot_steps=_build_cot(intent_res, None, impact, None), llm_used=used,
        )

    # 查询进度
    if intent_res.intent == "query_progress":
        progress = goal_service.compute_progress(goal)
        impact = GoalImpact(has_goal=goal is not None, note=_progress_note(progress))
        reply, used = _persona_text(role, message, None, impact, None)
        return ChatResponse(
            reply=reply, role=role, intent="query_progress", impact=impact,
            cot_steps=_build_cot(intent_res, None, impact, None), llm_used=used,
        )

    # 闲聊
    if intent_res.intent == "chitchat":
        impact = GoalImpact(has_goal=goal is not None, note=_goal_hint(goal))
        reply, used = _persona_text(role, message, None, impact, None)
        return ChatResponse(
            reply=reply, role=role, intent="chitchat",
            cot_steps=_build_cot(intent_res, None, impact, None), llm_used=used,
        )

    # 消费意图：完整推理链
    price = price_db.lookup(intent_res.item, intent_res.price, message)
    impact = goal_service.compute_impact(goal, intent_res.price)
    verdict = decide_verdict(price, impact)
    reply, used = _persona_text(role, message, price, impact, verdict)

    return ChatResponse(
        reply=reply,
        role=role,
        intent="purchase",
        verdict=verdict,
        price=price,
        impact=impact,
        cot_steps=_build_cot(intent_res, price, impact, verdict),
        llm_used=used,
    )


def _persona_text(role, message, price, impact, verdict) -> tuple[str, bool]:
    """优先 LLM，失败回退本地模板。返回 (文本, 是否用了LLM)。"""
    system = prompts.system_prompt(role)
    user_ctx = prompts.build_user_context(message, price, impact, verdict)
    text = llm.chat(system, user_ctx)
    if text:
        return text, True
    return prompts.fallback_reply(role, message, price, impact, verdict), False


def _goal_hint(goal) -> str:
    if not goal:
        return "你还没设定攒钱目标，左边面板设一个吧，我好帮你盯着钱包～"
    return f"你的攒钱目标「{goal.name}」，目标 ¥{goal.target_amount:.0f}，已攒 ¥{goal.saved_amount:.0f}。"


def _progress_note(progress) -> str:
    if not progress.goal:
        return "还没设定攒钱目标哦，先定个小目标吧～"
    g = progress.goal
    note = f"目标「{g.name}」：已攒 ¥{g.saved_amount:.0f} / ¥{g.target_amount:.0f}，进度 {progress.progress_ratio*100:.1f}%，还差 ¥{progress.remaining:.0f}。"
    if progress.months_to_go is not None:
        note += f"按当前速度约还需 {progress.months_to_go} 个月。"
    return note
