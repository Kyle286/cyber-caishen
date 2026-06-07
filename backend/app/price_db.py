"""内置模拟商品库与比价逻辑。

不依赖外部网络，模拟"检索同类商品底价"。每个品类含均价/底价/高价区间，
并支持按关键词模糊匹配到品类。
"""
from __future__ import annotations

from typing import Optional

from .models import PriceInfo

# 品类配置：关键词 -> (展示名, 均价, 底价, 高价)
_CATEGORIES: dict[str, dict] = {
    "盲盒": {"aliases": ["盲盒", "潮玩", "泡泡玛特", "labubu", "molly"], "avg": 320, "low": 199, "high": 999},
    "球鞋": {"aliases": ["球鞋", "鞋", "运动鞋", "aj", "椰子", "篮球鞋"], "avg": 899, "low": 399, "high": 2999},
    "咖啡": {"aliases": ["咖啡", "拿铁", "美式", "星巴克", "瑞幸"], "avg": 22, "low": 9, "high": 45},
    "口红": {"aliases": ["口红", "唇釉", "彩妆", "化妆品"], "avg": 280, "low": 89, "high": 680},
    "手机": {"aliases": ["手机", "iphone", "安卓", "华为", "小米手机"], "avg": 4999, "low": 1299, "high": 12999},
    "耳机": {"aliases": ["耳机", "airpods", "蓝牙耳机", "降噪耳机"], "avg": 999, "low": 199, "high": 2999},
    "包": {"aliases": ["包", "包包", "手袋", "背包", "奢侈品包"], "avg": 1500, "low": 199, "high": 39999},
    "游戏": {"aliases": ["游戏", "皮肤", "充值", "氪金", "switch", "ps5", "steam"], "avg": 298, "low": 30, "high": 3999},
    "衣服": {"aliases": ["衣服", "外套", "卫衣", "裙子", "裤子", "t恤", "羽绒服"], "avg": 350, "low": 79, "high": 2999},
    "演唱会": {"aliases": ["演唱会", "门票", "票", "演出", "livehouse"], "avg": 880, "low": 280, "high": 2680},
    "零食": {"aliases": ["零食", "奶茶", "蛋糕", "外卖", "炸鸡", "火锅"], "avg": 45, "low": 12, "high": 200},
    "数码配件": {"aliases": ["键盘", "鼠标", "充电宝", "数据线", "手机壳", "支架"], "avg": 199, "low": 39, "high": 1299},
}

# 未匹配到品类时的通用区间
_DEFAULT = {"avg": 300, "low": 99, "high": 1500}


def _match_category(item: Optional[str], text: str) -> Optional[str]:
    """根据物品名或原文匹配品类。"""
    haystack = f"{item or ''} {text}".lower()
    for name, cfg in _CATEGORIES.items():
        for alias in cfg["aliases"]:
            if alias.lower() in haystack:
                return name
    return None


def lookup(item: Optional[str], price: Optional[float], text: str = "") -> PriceInfo:
    """比价：返回同类商品价格区间与溢价率评价。"""
    category = _match_category(item, text)
    cfg = _CATEGORIES.get(category, _DEFAULT) if category else _DEFAULT
    display_item = item or category or "这件商品"
    avg, low, high = float(cfg["avg"]), float(cfg["low"]), float(cfg["high"])

    overprice_ratio = None
    if price is not None and low > 0:
        overprice_ratio = round((price - low) / low, 3)

    comment = _build_comment(price, avg, low, overprice_ratio)
    return PriceInfo(
        item=display_item,
        category=category or "未知品类",
        user_price=price,
        avg_price=avg,
        lowest_price=low,
        highest_price=high,
        overprice_ratio=overprice_ratio,
        comment=comment,
    )


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
