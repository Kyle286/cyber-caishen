"""两套人格 System Prompt、本地回退模板与补充建议生成。"""
from __future__ import annotations

import re
from typing import Optional

from . import llm
from .models import GoalImpact, ImpulseScore, PriceInfo, Verdict

CAISHEN_SYSTEM = """你是"赛博财神爷"，赛博朋克世界里掌管钱财的财神。
【人设】慈祥、接地气、爱发钱也爱替人省钱，带点理财智慧和老北京财神的喜庆。
【风格】温暖、幽默、善用比喻，偶尔"财源滚滚""恭喜发财"，但绝不油腻；口语化，可用 emoji。
【内容要求】用连贯口语一次性说完，不要分节、不要小标题、不要写「裁决理由」「人格化收尾」「财神爷叨叨」等字样，不要用 ** 加粗标题。
先用 2～3 句话解释为何建议劝退/鼓励/理性提醒，必须引用溢价率、占目标比例、延后天数等至少 2 个具体数字；再自然接上财神语气祝福或提醒。
控制在 150 字以内。"""

BESTIE_SYSTEM = """你是用户的"毒舌闺蜜"，嘴上不饶人、心里超爱用户。
【人设】犀利、毒舌、爱玩网络梗，看不得姐妹乱花钱交智商税。
【风格】直接开怼但带着关心；口语化，可用 emoji。
【内容要求】用连贯口语一次性说完，不要分节、不要小标题、不要写「裁决理由」「人格化收尾」「闺蜜开怼」等字样，不要用 ** 加粗标题。
先用 2～3 句话解释为何建议劝退/鼓励/理性提醒，必须引用溢价率、占目标比例、延后天数等至少 2 个具体数字；再自然损两句或勉强放行。
控制在 150 字以内。"""

SUGGESTIONS_SYSTEM = """你是理财建议助手。根据用户消费分析，输出 2～3 条简短、可执行的建议。
类型可包括：平替方案、等等党/蹲底价、冷静期、先攒够再买、二手/租赁、设定预算上限等。
每条独占一行，不要编号，不要多余解释，共 2～3 条。"""


def system_prompt(role: str) -> str:
    return BESTIE_SYSTEM if role == "bestie" else CAISHEN_SYSTEM


# 模型偶发仍会输出的小节标题，统一剥掉
_SECTION_LABEL = re.compile(
    r"\*{0,2}(?:裁决理由|人格化收尾|财神爷叨叨|闺蜜开怼|理性分析)[：:]*\*{0,2}\s*"
)


def sanitize_reply(text: str) -> str:
    """去掉回复里不应展示的结构化小标题。"""
    cleaned = _SECTION_LABEL.sub("", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def build_user_context(
    message: str,
    price: PriceInfo | None,
    impact: GoalImpact | None,
    verdict: Verdict | None,
    impulse: ImpulseScore | None = None,
    oc: list[str] | None = None,
) -> str:
    """把结构化分析喂给 LLM 作为推理依据（CoT 上下文）。"""
    lines = [f"用户原话：{message}", ""]
    if price:
        lines += [
            "【同类比价数据】",
            f"- 物品：{price.item}（品类：{price.category}）",
            f"- 用户报价：{price.user_price}",
            f"- 市场底价：¥{price.lowest_price:.0f}，均价：¥{price.avg_price:.0f}，高价：¥{price.highest_price:.0f}",
        ]
        if price.overprice_ratio is not None:
            lines.append(f"- 相对底价溢价率：{price.overprice_ratio*100:.0f}%")
        lines.append("")
    if impact:
        lines += ["【攒钱目标影响】", f"- {impact.note}", ""]
    if oc:
        lines += ["【机会成本】", "- 这笔钱 " + "，".join(oc), ""]
    if impulse:
        lines += ["【冲动指数】", f"- {impulse.score}/100（{impulse.level}）：" + "、".join(impulse.reasons), ""]
    if verdict:
        verdict_cn = {"discourage": "建议劝退", "encourage": "可以鼓励", "neutral": "理性提醒"}[verdict]
        lines.append(f"【系统裁决】{verdict_cn}（回复必须先解释为何是这个裁决，再人格化表达）")
    return "\n".join(lines)


def rule_suggestions(
    price: Optional[PriceInfo],
    verdict: Optional[Verdict],
    impact: Optional[GoalImpact],
) -> list[str]:
    """规则生成的补充建议（LLM 不可用时的兜底）。"""
    out: list[str] = []
    if verdict == "discourage":
        if price and price.lowest_price:
            out.append(f"等等党：蹲到约 ¥{price.lowest_price:.0f} 的底价再买，别急着当大冤种")
        if price and price.save_if_lowest and price.save_if_lowest > 50:
            out.append(f"平替思路：选均价 ¥{price.avg_price:.0f} 档同类，或直接省下 ¥{price.save_if_lowest:.0f}")
        if impact and impact.delay_days:
            out.append(f"先攒钱：这笔消费会让目标延后 {impact.delay_days} 天，不如存进目标")
        if not out:
            out.append("设 24 小时冷静期，睡醒再决定要不要买")
    elif verdict == "encourage":
        out.append("价格还算合理，真要买记得货比三家")
        if price:
            out.append(f"小 tip：能谈到 ¥{price.lowest_price:.0f} 附近再入手更划算")
    else:
        out.append("再比比价，别冲动下单")
        out.append("加入购物车放三天，三天后还想要再买")
    return out[:3]


def generate_suggestions(
    user_ctx: str,
    price: Optional[PriceInfo],
    verdict: Optional[Verdict],
    impact: Optional[GoalImpact],
    model: Optional[str] = None,
    llm_ok: bool = False,
) -> list[str]:
    """生成模型补充建议；LLM 优先，失败回退规则。"""
    rules = rule_suggestions(price, verdict, impact)
    if not llm_ok:
        return rules
    text = llm.chat(
        SUGGESTIONS_SYSTEM,
        user_ctx + "\n\n请基于以上分析，输出 2～3 条补充建议（平替/等等党/冷静期等）。",
        temperature=0.7,
        model=model,
    )
    if not text:
        return rules
    lines = [
        ln.strip().lstrip("0123456789.-•、)） ")
        for ln in text.strip().split("\n")
        if ln.strip() and len(ln.strip()) > 4
    ]
    return lines[:3] if lines else rules


# ---- 本地回退模板（无 LLM 时使用，保证演示可用）----

def fallback_reply(role: str, message: str, price: PriceInfo | None, impact: GoalImpact | None, verdict: Verdict | None) -> str:
    if role == "bestie":
        return _bestie_fallback(price, impact, verdict)
    return _caishen_fallback(price, impact, verdict)


def _caishen_fallback(price, impact, verdict) -> str:
    if verdict is None and impact and impact.note:
        return f"财神说道：{impact.note}"
    reasons: list[str] = []
    if price and price.user_price is not None and price.overprice_ratio is not None:
        reasons.append(
            f"你这「{price.item}」要 ¥{price.user_price:.0f}，底价才 ¥{price.lowest_price:.0f}，溢价 {price.overprice_ratio*100:.0f}%"
        )
    if impact and impact.has_goal and impact.goal_impact_ratio is not None:
        reasons.append(f"占你攒钱目标 {impact.goal_impact_ratio*100:.1f}%")
    if impact and impact.delay_days:
        reasons.append(f"还会让目标延后 {impact.delay_days} 天")
    if verdict == "discourage":
        closing = "所以财神劝退：先把钱袋子捂住，攒够了再犒劳自己！💰"
    elif verdict == "encourage":
        closing = "价格合理占比也低，财神准了，偶尔对自己好点！🧧"
    else:
        closing = "再想想，理性消费财源广进～"
    body = "，".join(reasons)
    return f"财神我掐指一算～{body}，{closing}" if body else f"财神我掐指一算～{closing}"


def _bestie_fallback(price, impact, verdict) -> str:
    if verdict is None and impact and impact.note:
        return f"姐妹跟你说：{impact.note}"
    reasons: list[str] = []
    if price and price.user_price is not None and price.overprice_ratio is not None:
        reasons.append(
            f"「{price.item}」¥{price.user_price:.0f} vs 底价 ¥{price.lowest_price:.0f}，溢价 {price.overprice_ratio*100:.0f}%"
        )
    if impact and impact.has_goal and impact.goal_impact_ratio is not None:
        reasons.append(f"占目标 {impact.goal_impact_ratio*100:.1f}%")
    if impact and impact.delay_days:
        reasons.append(f"延后 {impact.delay_days} 天")
    if verdict == "discourage":
        closing = "劝退！放下手机别给商家送钱😭"
    elif verdict == "encourage":
        closing = "行吧这次划算，准你买，别上瘾！"
    else:
        closing = "再想想，冲动是魔鬼。"
    body = "，".join(reasons)
    return f"姐妹听我一句👀 {body}，{closing}" if body else f"姐妹听我一句👀 {closing}"
