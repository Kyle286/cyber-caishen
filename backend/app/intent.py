"""意图识别：从用户自然语言中抽取意图类型、物品名与金额。

纯规则实现（正则 + 品类词典 + 关键词），不依赖 LLM，保证离线可用、可单测。
设计要点：
- 物品识别优先复用 price_db 的品类词典，位置无关，避免抓到价格数字/助词等垃圾。
- 金额识别支持多金额，并按"离物品最近"择优，区分'月薪3000买2万的包'这类语义角色。
- 处理否定/克制（resist）、纯询价、无金额的攒钱意图、以及多轮追问的上下文补槽。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from . import price_db
from .models import ChatContext, IntentType

_UNIT_MULTIPLIER = {"块": 1, "元": 1, "圆": 1, "百": 100, "千": 1000, "万": 10000, "w": 10000, "k": 1000}

_PAT_BIG_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(万|千|w|k|W|K)")
_PAT_CURRENCY_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(块|元|圆|rmb)", re.IGNORECASE)
_PAT_CURRENCY_SYMBOL = re.compile(r"[¥￥$]\s*(\d+(?:\.\d+)?)")
_PAT_BARE = re.compile(r"(?<![A-Za-z])(\d{2,}(?:\.\d+)?)")

_GOAL_KEYWORDS = ["攒钱", "存钱", "攒够", "存够", "想攒", "想存", "攒个", "存个", "攒到", "存到", "目标", "攒下"]
_PROGRESS_KEYWORDS = ["进度", "攒了多少", "还差多少", "存了多少", "目标进度", "攒得怎么样", "还要多久", "查进度", "攒到哪"]
_PURCHASE_KEYWORDS = ["买", "购", "入手", "下单", "剁手", "拿下", "冲", "种草", "想要", "心动", "囤", "付款", "下血本"]
_NEGATION_PATTERNS = ["不想买", "不买", "别买", "算了", "忍住", "忍一忍", "不要了", "退了", "不剁手", "管住手", "戒了", "不能买", "劝我别", "帮我忍", "克制"]
_FOLLOWUP_HINTS = ["那", "换", "其他", "别的", "再", "便宜点", "便宜些", "便宜的", "贵点", "划算点", "换个", "那个呢"]


@dataclass
class IntentResult:
    intent: IntentType
    item: Optional[str] = None
    price: Optional[float] = None
    target_amount: Optional[float] = None
    category: Optional[str] = None
    raw: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    is_followup: bool = False


def _collect_amounts(text: str) -> list[tuple[int, float]]:
    candidates: list[tuple[int, float]] = []
    for m in _PAT_BIG_UNIT.finditer(text):
        unit = m.group(2).lower()
        candidates.append((m.start(), float(m.group(1)) * _UNIT_MULTIPLIER.get(unit, 1)))
    for m in _PAT_CURRENCY_UNIT.finditer(text):
        candidates.append((m.start(), float(m.group(1))))
    for m in _PAT_CURRENCY_SYMBOL.finditer(text):
        candidates.append((m.start(), float(m.group(1))))
    for m in _PAT_BARE.finditer(text):
        end = m.end()
        if end < len(text) and text[end].isascii() and text[end].isalpha():
            continue
        candidates.append((m.start(), float(m.group(1))))
    candidates.sort(key=lambda c: c[0])
    return candidates


def extract_price(text: str) -> Optional[float]:
    """抽取金额：返回文本中最靠前出现的金额（兼容历史用法）。"""
    amounts = _collect_amounts(text)
    return amounts[0][1] if amounts else None


def _price_nearest(amounts: list[tuple[int, float]], pos: Optional[int]) -> Optional[float]:
    """从候选金额中选离 pos 最近的；pos 为空时取最靠前的。"""
    if not amounts:
        return None
    if pos is None:
        return amounts[0][1]
    return min(amounts, key=lambda c: abs(c[0] - pos))[1]


_PARTICLES = "了个只件台双杯套份盒的这那"
_VERB_GROUP = r"(?:买|购入|购买|入手|下单|拿下|冲|想要|种草|拔草)"
_ITEM_AFTER_VERB = re.compile(_VERB_GROUP + r"([^，。,.!？!~\s]{1,16})")


def extract_item(text: str) -> Optional[str]:
    """兜底物品识别（品类词典未命中时）：取购买动词之后的名词，清洗量词/数字/单位。"""
    m = _ITEM_AFTER_VERB.search(text)
    if not m:
        return None
    s = m.group(1).lstrip(_PARTICLES)
    s = re.split(r"[0-9¥￥$]", s)[0]  # 截断到价格/数字之前
    s = s.rstrip("的").strip()
    return s[:8] if s else None


def _hit(text: str, keywords: list[str]) -> list[str]:
    return [k for k in keywords if k in text]


def _resolve_item(text: str) -> tuple[Optional[str], Optional[str], Optional[int]]:
    """返回 (item 展示名, category, item 在文本中的位置)。"""
    match = price_db.detect_category(text)
    if match:
        # 英文别名（如 aj/iphone）用品类名展示更友好
        item = match.category if match.alias.isascii() else match.alias
        return item, match.category, match.pos
    item = extract_item(text)
    pos = text.find(item) if item else None
    return item, None, pos


def recognize(text: str, context: Optional[ChatContext] = None) -> IntentResult:
    """识别意图。优先级：克制 > 查询进度 > 设定目标 > 消费 > 闲聊。"""
    raw = text.strip()
    amounts = _collect_amounts(raw)
    progress_hits = _hit(raw, _PROGRESS_KEYWORDS)
    goal_hits = _hit(raw, _GOAL_KEYWORDS)
    purchase_hits = _hit(raw, _PURCHASE_KEYWORDS)
    negation_hits = [p for p in _NEGATION_PATTERNS if p in raw]
    item, category, item_pos = _resolve_item(raw)

    # 多轮追问补槽：本句没识别出具体品类，但含'那/便宜点/换个'等追问词且有上下文，
    # 则复用上一笔被讨论的物品（如'那买便宜点的呢'）
    is_followup = False
    if category is None and context and context.last_item and any(h in raw for h in _FOLLOWUP_HINTS):
        item = context.last_item
        item_pos = None
        is_followup = True

    # 1. 克制 / 否定：用户主动表示不买或求劝退
    if negation_hits:
        return IntentResult(
            intent="resist",
            item=item,
            price=_price_nearest(amounts, item_pos),
            category=category,
            raw=raw,
            matched_keywords=negation_hits,
        )

    # 2. 查询进度
    if progress_hits and not (purchase_hits and amounts):
        return IntentResult(intent="query_progress", raw=raw, matched_keywords=progress_hits)

    # 3. 设定目标
    if goal_hits:
        # 目标金额取离攒钱关键词最近的金额；没有金额则留空，引导用户补充
        goal_pos = min((raw.find(k) for k in goal_hits if raw.find(k) >= 0), default=None)
        target = _price_nearest(amounts, goal_pos)
        return IntentResult(
            intent="set_goal",
            target_amount=target,
            item=item,
            category=category,
            raw=raw,
            matched_keywords=goal_hits,
        )

    # 4. 消费：显式购买词、追问复用，或"有价格 + 有物品/品类"的询价场景
    if purchase_hits or is_followup or (amounts and (item or category)):
        return IntentResult(
            intent="purchase",
            item=item,
            price=_price_nearest(amounts, item_pos),
            category=category,
            raw=raw,
            matched_keywords=purchase_hits,
            is_followup=is_followup,
        )

    # 5. 其余归为闲聊
    return IntentResult(intent="chitchat", raw=raw)
