"""意图识别：从用户自然语言中抽取意图类型、物品名与金额。

纯规则实现（正则 + 关键词），不依赖 LLM，保证离线可用、可单测。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .models import IntentType

# 中文数字单位映射
_UNIT_MULTIPLIER = {"块": 1, "元": 1, "圆": 1, "百": 100, "千": 1000, "万": 10000, "w": 10000, "k": 1000}

# 金额匹配模式（按强度分组，最终统一按"在文本中出现的位置"择优）
_PAT_BIG_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(万|千|w|k|W|K)")
_PAT_CURRENCY_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(块|元|圆|rmb)", re.IGNORECASE)
_PAT_CURRENCY_SYMBOL = re.compile(r"[¥￥$]\s*(\d+(?:\.\d+)?)")
# 兜底裸数字：≥2 位，且前面不紧跟字母（避免把型号 iphone15 的 15 当价格）
_PAT_BARE = re.compile(r"(?<![A-Za-z])(\d{2,}(?:\.\d+)?)")

# 设定目标关键词
_GOAL_KEYWORDS = ["攒钱", "存钱", "目标", "攒够", "存够", "想攒", "想存", "攒个", "存个", "攒到", "存到"]
# 查询进度关键词
_PROGRESS_KEYWORDS = ["进度", "攒了多少", "还差多少", "存了多少", "目标进度", "攒得怎么样", "还要多久", "查进度"]
# 消费意图关键词
_PURCHASE_KEYWORDS = ["买", "购", "入手", "下单", "剁手", "拿下", "冲", "种草", "想要", "心动"]

# 物品名：尝试抽取"买/入手 + 物品"或"X个/只/件 + 物品"
_ITEM_AFTER_VERB = re.compile(r"(?:买|购入|购买|入手|下单|拿下|冲|想要|种草)\s*(?:个|只|件|台|双|杯|套|份|盒)?\s*([\u4e00-\u9fa5A-Za-z0-9]{1,12})")
_QUANTIFIER_ITEM = re.compile(r"\d+\s*(?:个|只|件|台|双|杯|套|份|盒)\s*([\u4e00-\u9fa5A-Za-z0-9]{1,12})")


@dataclass
class IntentResult:
    intent: IntentType
    item: Optional[str] = None
    price: Optional[float] = None
    target_amount: Optional[float] = None
    raw: str = ""
    matched_keywords: list[str] = field(default_factory=list)


def extract_price(text: str) -> Optional[float]:
    """抽取金额。

    收集所有候选金额（带单位/货币符号/裸数字），返回**在文本中最靠前出现**的那个，
    因为用户正在讨论的消费/目标金额通常先出现。避免出现"先命中后段大额单位"
    （如"想买 800 的鞋，攒到 2 万" 错抓成 20000）这类位置无关的优先级 bug。
    """
    candidates: list[tuple[int, float]] = []

    for m in _PAT_BIG_UNIT.finditer(text):
        unit = m.group(2).lower()
        candidates.append((m.start(), float(m.group(1)) * _UNIT_MULTIPLIER.get(unit, 1)))

    for m in _PAT_CURRENCY_UNIT.finditer(text):
        candidates.append((m.start(), float(m.group(1))))

    for m in _PAT_CURRENCY_SYMBOL.finditer(text):
        candidates.append((m.start(), float(m.group(1))))

    for m in _PAT_BARE.finditer(text):
        # 排除数字紧跟 ASCII 字母的情况（如 15plus），避免误抓型号
        end = m.end()
        if end < len(text) and text[end].isascii() and text[end].isalpha():
            continue
        candidates.append((m.start(), float(m.group(1))))

    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0])
    return candidates[0][1]


def extract_item(text: str) -> Optional[str]:
    """抽取物品名。"""
    for pat in (_ITEM_AFTER_VERB, _QUANTIFIER_ITEM):
        m = pat.search(text)
        if m:
            item = m.group(1).strip()
            # 过滤掉抽到金额数字/单位的情况
            if item and not re.fullmatch(r"\d+", item):
                return item
    return None


def _hit(text: str, keywords: list[str]) -> list[str]:
    return [k for k in keywords if k in text]


def recognize(text: str) -> IntentResult:
    """识别意图。优先级：查询进度 > 设定目标 > 消费 > 闲聊。"""
    raw = text.strip()
    progress_hits = _hit(raw, _PROGRESS_KEYWORDS)
    goal_hits = _hit(raw, _GOAL_KEYWORDS)
    purchase_hits = _hit(raw, _PURCHASE_KEYWORDS)

    price = extract_price(raw)

    # 查询进度：命中进度关键词且不含明显消费动作
    if progress_hits and not (purchase_hits and price):
        return IntentResult(intent="query_progress", raw=raw, matched_keywords=progress_hits)

    # 设定目标：命中攒钱关键词且有金额
    if goal_hits and price is not None:
        return IntentResult(
            intent="set_goal",
            target_amount=price,
            item=extract_item(raw),
            raw=raw,
            matched_keywords=goal_hits,
        )

    # 消费：命中购买关键词
    if purchase_hits:
        return IntentResult(
            intent="purchase",
            item=extract_item(raw),
            price=price,
            raw=raw,
            matched_keywords=purchase_hits,
        )

    # 仅有金额也按消费处理（如"800的盲盒"）
    if price is not None and extract_item(raw):
        return IntentResult(intent="purchase", item=extract_item(raw), price=price, raw=raw)

    return IntentResult(intent="chitchat", raw=raw)
