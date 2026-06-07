from app import intent


def test_extract_price_with_unit():
    assert intent.extract_price("我想花800块买个盲盒") == 800
    assert intent.extract_price("这个手机要5999元") == 5999


def test_extract_price_wan_unit():
    assert intent.extract_price("攒钱目标1万") == 10000
    assert intent.extract_price("想攒2.5万") == 25000


def test_extract_price_symbol():
    assert intent.extract_price("一双鞋¥1299") == 1299


def test_recognize_purchase():
    r = intent.recognize("我好想花800块买个盲盒")
    assert r.intent == "purchase"
    assert r.price == 800
    assert r.item == "盲盒"


def test_recognize_set_goal():
    r = intent.recognize("我想攒钱买iPhone，目标6000")
    assert r.intent == "set_goal"
    assert r.target_amount == 6000


def test_recognize_query_progress():
    r = intent.recognize("我的攒钱进度怎么样了")
    assert r.intent == "query_progress"


def test_recognize_chitchat():
    r = intent.recognize("你好呀")
    assert r.intent == "chitchat"
