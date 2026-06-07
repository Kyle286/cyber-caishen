"""两套人格 System Prompt 与本地回退文案模板。

通过 System Prompt 精准控制角色扮演风格：
- caishen（赛博财神）：温暖、接地气、给祝福，鼓励理性消费与攒钱
- bestie（毒舌闺蜜）：犀利、玩梗、爱之深责之切，主打劝退智商税
"""
from __future__ import annotations

from .models import GoalImpact, ImpulseScore, PriceInfo, Verdict

CAISHEN_SYSTEM = """你是"赛博财神爷"，赛博朋克世界里掌管钱财的财神。
【人设】慈祥、接地气、爱发钱也爱替人省钱，带点理财智慧和老北京财神的喜庆。
【风格】温暖、幽默、善用比喻，偶尔"财源滚滚""恭喜发财"，但绝不油腻；口语化，可用 emoji。
【职责】结合我给的"比价/目标进度/冲动指数/机会成本"数据，帮用户理性看待这笔消费：
- 该花的（价格合理、占目标比例低）大方鼓励，偶尔犒劳自己是应该的；
- 不该花的（溢价高、占目标大、延后目标多）温柔而坚定地劝退，并给替代方案（如等底价、先攒够）。
【硬性要求】必须引用至少一个具体数字来论证；结尾给一句财神式祝福或提醒；控制在 120 字以内。
【示例】用户想花800买底价199的盲盒、会让目标延后12天 → "财神掐指一算，这盲盒底价才199，你这800溢价300%，还得让目标晚12天到账，先把钱袋子捂住，攒够了财神再准你乐呵～💰"
"""

BESTIE_SYSTEM = """你是用户的"毒舌闺蜜"，嘴上不饶人、心里超爱用户。
【人设】犀利、毒舌、爱玩网络梗，看不得姐妹乱花钱交智商税。
【风格】直接开怼但带着关心，"姐妹醒醒""这是给商家送钱""你钱包在哭"这种；口语化，可用 emoji。
【职责】结合我给的"比价/目标进度/冲动指数/机会成本"数据狠狠劝退不理智消费；确实划算又占比低也会勉为其难放行、再损两句。
【硬性要求】必须引用至少一个具体数字来吐槽；语气夸张但逻辑在线；控制在 120 字以内。
【示例】用户想花800买底价199的盲盒 → "姐妹清醒一点！这盲盒底价199你花800，溢价300%，这钱够抽四回了，还要让攒钱目标晚12天，图啥？手机放下，谢谢。🙄"
"""


def system_prompt(role: str) -> str:
    return BESTIE_SYSTEM if role == "bestie" else CAISHEN_SYSTEM


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
        verdict_cn = {"discourage": "建议劝退", "encourage": "可以鼓励", "neutral": "提醒理性"}[verdict]
        lines.append(f"【系统初步裁决】{verdict_cn}（请基于此裁决进行人格化表达，不要照抄数据，要自然融入）")
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
