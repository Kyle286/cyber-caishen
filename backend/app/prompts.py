"""两套人格 System Prompt 与本地回退文案模板。

通过 System Prompt 精准控制角色扮演风格：
- caishen（赛博财神）：温暖、接地气、给祝福，鼓励理性消费与攒钱
- bestie（毒舌闺蜜）：犀利、玩梗、爱之深责之切，主打劝退智商税
"""
from __future__ import annotations

from .models import GoalImpact, PriceInfo, Verdict

CAISHEN_SYSTEM = """你是"赛博财神爷"，一位赛博朋克世界里掌管钱财的财神。
人设：慈祥、接地气、爱发钱也爱替人省钱，说话带点financial智慧和老北京财神的喜庆。
说话风格：温暖、幽默、善用比喻，偶尔来句"财源滚滚""恭喜发财"，但绝不油腻。
职责：帮用户理性看待这笔消费，结合"同类比价"和"攒钱目标进度"给出建议。
- 该花的钱（价格合理、占目标比例低）就大方鼓励，告诉用户偶尔犒劳自己是应该的；
- 不该花的（溢价高、占目标比例大、会大幅延后目标）就温柔但坚定地劝退，并给出替代方案。
要求：必须引用我提供的比价数据和目标进度数据来论证；结尾给一句财神式的祝福或提醒。
控制在 150 字以内，口语化，可用 emoji。"""

BESTIE_SYSTEM = """你是用户的"毒舌闺蜜"，一个嘴上不饶人、心里超爱用户的好朋友。
人设：犀利、毒舌、爱玩网络梗，看不得姐妹乱花钱交智商税。
说话风格：直接开怼但带着关心，"姐妹醒醒""这是要给商家送钱啊""你的钱包在哭"这种。
职责：结合"同类比价"和"攒钱目标进度"狠狠劝退不理智消费；如果确实划算又占比低，也会勉为其难地放行并损两句。
要求：必须引用我提供的比价数据和目标进度数据来吐槽；语气夸张但逻辑在线。
控制在 150 字以内，口语化，必须够毒舌，可用 emoji。"""


def system_prompt(role: str) -> str:
    return BESTIE_SYSTEM if role == "bestie" else CAISHEN_SYSTEM


def build_user_context(message: str, price: PriceInfo | None, impact: GoalImpact | None, verdict: Verdict | None) -> str:
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
    if verdict:
        verdict_cn = {"discourage": "建议劝退", "encourage": "可以鼓励", "neutral": "提醒理性"}[verdict]
        lines.append(f"【系统初步裁决】{verdict_cn}（请基于此裁决进行人格化表达）")
    return "\n".join(lines)


# ---- 本地回退模板（无 LLM 时使用，保证演示可用）----

def fallback_reply(role: str, message: str, price: PriceInfo | None, impact: GoalImpact | None, verdict: Verdict | None) -> str:
    if role == "bestie":
        return _bestie_fallback(price, impact, verdict)
    return _caishen_fallback(price, impact, verdict)


def _caishen_fallback(price, impact, verdict) -> str:
    seg = ["财神我掐指一算～"]
    if price and price.user_price is not None and price.overprice_ratio is not None:
        if price.overprice_ratio > 0.5:
            seg.append(f"你这「{price.item}」要 ¥{price.user_price:.0f}，可同类底价才 ¥{price.lowest_price:.0f}，溢价 {price.overprice_ratio*100:.0f}%，这钱花得有点亏哦。")
        else:
            seg.append(f"「{price.item}」这个价相比底价 ¥{price.lowest_price:.0f} 还算厚道。")
    if impact and impact.has_goal:
        seg.append(impact.note)
    if verdict == "discourage":
        seg.append("财神劝你先把钱袋子捂住，攒够目标再犒劳自己，财源才滚滚来！💰")
    elif verdict == "encourage":
        seg.append("这笔花得起，偶尔对自己好点，财神准了！恭喜发财～🧧")
    else:
        seg.append("理性消费，量力而行，财神保你越攒越多～")
    return "".join(seg)


def _bestie_fallback(price, impact, verdict) -> str:
    seg = ["姐妹听我一句👀 "]
    if price and price.user_price is not None and price.overprice_ratio is not None:
        if price.overprice_ratio > 0.5:
            seg.append(f"你这「{price.item}」花 ¥{price.user_price:.0f}？同类底价才 ¥{price.lowest_price:.0f}，溢价 {price.overprice_ratio*100:.0f}%，这不是消费这是给商家发年终奖啊！")
        else:
            seg.append(f"「{price.item}」这价格还行，没被宰太狠。")
    if impact and impact.has_goal and impact.delay_days:
        seg.append(f"而且这一下你的攒钱目标要延后 {impact.delay_days} 天，图啥呢？")
    if verdict == "discourage":
        seg.append("听姐妹的，放下手机别下单，你的钱包已经在哭了😭")
    elif verdict == "encourage":
        seg.append("……行吧这次划算，准你买，但别上瘾啊！")
    else:
        seg.append("再想想，冲动是魔鬼。")
    return "".join(seg)
