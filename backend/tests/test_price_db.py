from app import price_db


def test_lookup_known_category():
    info = price_db.lookup("盲盒", 800, "我想花800块买个盲盒")
    assert info.category == "盲盒"
    assert info.lowest_price == 199
    assert info.overprice_ratio is not None
    assert info.overprice_ratio > 1.0  # 800 相对 199 溢价超过 100%


def test_lookup_unknown_category_uses_default():
    info = price_db.lookup("不存在的东西", 300, "买个不存在的东西")
    assert info.category == "未知品类"
    assert info.lowest_price == 99


def test_lookup_no_price():
    info = price_db.lookup("咖啡", None, "想喝咖啡")
    assert info.user_price is None
    assert info.overprice_ratio is None
    assert info.avg_price == 22


def test_overprice_comment_for_bargain():
    info = price_db.lookup("咖啡", 5, "5块的咖啡")
    assert info.overprice_ratio <= 0
    assert "捡漏" in info.comment
