"""内置模拟商品库与比价逻辑。

不依赖外部网络，模拟"检索同类商品底价"。每个品类含均价/底价/高价区间，
并支持按关键词模糊匹配到品类（detect_category），供意图识别复用。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import PriceInfo

# 品类配置：展示名 -> {aliases, avg, low, high}
_CATEGORIES: dict[str, dict] = {
    "盲盒": {"aliases": ["盲盒", "潮玩", "泡泡玛特", "labubu", "molly"], "avg": 320, "low": 199, "high": 999},
    "球鞋": {"aliases": ["球鞋", "运动鞋", "篮球鞋", "aj", "椰子", "yeezy", "鞋"], "avg": 899, "low": 399, "high": 2999},
    "咖啡": {"aliases": ["咖啡", "拿铁", "美式", "星巴克", "瑞幸"], "avg": 22, "low": 9, "high": 45},
    "奶茶": {"aliases": ["奶茶", "喜茶", "茶饮", "霸王茶姬", "蜜雪"], "avg": 18, "low": 6, "high": 45},
    "口红": {"aliases": ["口红", "唇釉", "彩妆", "化妆品", "气垫", "粉底"], "avg": 280, "low": 89, "high": 680},
    "手机": {"aliases": ["手机", "iphone", "华为", "小米手机", "安卓机"], "avg": 4999, "low": 1299, "high": 12999},
    "耳机": {"aliases": ["耳机", "airpods", "蓝牙耳机", "降噪耳机"], "avg": 999, "low": 199, "high": 2999},
    "相机": {"aliases": ["相机", "微单", "单反", "拍立得", "gopro"], "avg": 5999, "low": 999, "high": 29999},
    "包": {"aliases": ["包包", "手袋", "背包", "奢侈品包", "包"], "avg": 1500, "low": 199, "high": 39999},
    "游戏": {"aliases": ["游戏", "皮肤", "氪金", "充值", "switch", "ps5", "steam"], "avg": 298, "low": 30, "high": 3999},
    "衣服": {"aliases": ["卫衣", "外套", "裙子", "裤子", "t恤", "羽绒服", "衣服"], "avg": 350, "low": 79, "high": 2999},
    "演唱会": {"aliases": ["演唱会", "门票", "演出", "livehouse", "音乐节"], "avg": 880, "low": 280, "high": 2680},
    "零食": {"aliases": ["零食", "蛋糕", "外卖", "炸鸡", "火锅", "甜品"], "avg": 45, "low": 12, "high": 200},
    "数码配件": {"aliases": ["键盘", "鼠标", "充电宝", "数据线", "手机壳", "支架"], "avg": 199, "low": 39, "high": 1299},
}

# 未匹配到品类时的通用区间
_DEFAULT = {"avg": 300, "low": 99, "high": 1500}

# 用于机会成本换算的日常小额参照物
_COFFEE_PRICE = 22.0
_MILKTEA_PRICE = 18.0


@dataclass
class CategoryMatch:
    category: str
    alias: str
    pos: int  # alias 在文本中首次出现的位置


def detect_category(text: str) -> Optional[CategoryMatch]:
    """在文本中识别商品品类，返回最靠前出现的别名匹配。"""
    low = text.lower()
    best: Optional[CategoryMatch] = None
    for name, cfg in _CATEGORIES.items():
        for alias in cfg["aliases"]:
            i = low.find(alias.lower())
            if i >= 0 and (best is None or i < best.pos):
                best = CategoryMatch(category=name, alias=alias, pos=i)
    return best


def lookup(item: Optional[str], price: Optional[float], text: str = "") -> PriceInfo:
    """比价：返回同类商品价格区间与溢价率评价。"""
    match = detect_category(f"{item or ''} {text}")
    category = match.category if match else None
    cfg = _CATEGORIES.get(category, _DEFAULT) if category else _DEFAULT
    display_item = item or category or "这件商品"
    avg, low, high = float(cfg["avg"]), float(cfg["low"]), float(cfg["high"])

    overprice_ratio = None
    save_if_lowest = None
    if price is not None and low > 0:
        overprice_ratio = round((price - low) / low, 3)
        save_if_lowest = round(max(price - low, 0), 2)

    comment = _build_comment(price, avg, low, overprice_ratio)
    return PriceInfo(
        item=display_item,
        category=category or "未知品类",
        user_price=price,
        avg_price=avg,
        lowest_price=low,
        highest_price=high,
        overprice_ratio=overprice_ratio,
        save_if_lowest=save_if_lowest,
        comment=comment,
    )


def opportunity_cost(price: Optional[float]) -> list[str]:
    """把金额换算成接地气的机会成本表达。"""
    if not price or price <= 0:
        return []
    out: list[str] = []
    coffees = int(price // _COFFEE_PRICE)
    if coffees >= 2:
        out.append(f"≈ {coffees} 杯咖啡（每杯约 ¥{_COFFEE_PRICE:.0f}）")
    milkteas = int(price // _MILKTEA_PRICE)
    if milkteas >= 2:
        out.append(f"≈ {milkteas} 杯奶茶（每杯约 ¥{_MILKTEA_PRICE:.0f}）")
    return out[:2]


def _build_comment(price, avg, low, ratio) -> str:
    if price is None:
        return f"同类商品市场底价约 ¥{low:.0f}，均价约 ¥{avg:.0f}。"
    if ratio is None:
        return f"同类底价约 ¥{low:.0f}。"
    if ratio <= 0:
        return f"你这个价 ¥{price:.0f} 已经低于市场底价 ¥{low:.0f}，捡漏了！"
    if ratio < 0.3:
        return f"略高于底价 ¥{low:.0f}，溢价 {ratio*100:.0f}%，还算合理。"
    if ratio < 1.0:
        return f"比底价 ¥{low:.0f} 贵了 {ratio*100:.0f}%，建议再比比价。"
    return f"比同类底价 ¥{low:.0f} 贵了 {ratio*100:.0f}%，妥妥的智商税预警！"
