from app import intent
from app.models import ChatContext


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


def test_extract_price_picks_earliest_amount():
    # 回归：不能因为后段"2万"带单位就忽略前面真正讨论的 800
    assert intent.extract_price("想买个800的鞋，攒到2万") == 800


def test_extract_price_ignores_model_number():
    # 回归：型号数字（紧跟字母）不应被当成价格
    assert intent.extract_price("我想买iphone15") is None
    assert intent.extract_price("入手ps5") is None


def test_extract_price_model_number_with_real_price():
    # 型号被忽略，真正的价格仍能识别
    assert intent.extract_price("iphone15 plus 想花6000买") == 6000


def test_recognize_purchase_without_price():
    r = intent.recognize("我想买个盲盒")
    assert r.intent == "purchase"
    assert r.price is None
    assert r.item == "盲盒"


def test_item_uses_category_no_garbage():
    # 回归：不能抓出"了个800的盲盒""奶茶25"这类垃圾物品名
    assert intent.recognize("我昨天买了个800的盲盒").item == "盲盒"
    assert intent.recognize("买杯奶茶25").item == "奶茶"
    assert intent.recognize("种草了一个199的小裙子").item == "裙子"


def test_item_before_verb_detected():
    r = intent.recognize("这个口红值不值得买")
    assert r.intent == "purchase"
    assert r.item == "口红"


def test_price_inquiry_without_buy_verb():
    r = intent.recognize("5000的相机贵吗")
    assert r.intent == "purchase"
    assert r.item == "相机"
    assert r.price == 5000


def test_nearest_amount_distinguishes_salary_from_price():
    # 月薪3000 vs 2万的包：物品价应取离物品最近的 2万
    r = intent.recognize("我月薪3000想买2万的包")
    assert r.intent == "purchase"
    assert r.item == "包"
    assert r.price == 20000


def test_resist_intent():
    for msg in ["我不想买了", "算了忍住", "帮我管住手"]:
        assert intent.recognize(msg).intent == "resist"


def test_set_goal_without_amount():
    r = intent.recognize("我想攒钱")
    assert r.intent == "set_goal"
    assert r.target_amount is None


def test_followup_reuses_context_item():
    ctx = ChatContext(last_item="盲盒", last_price=800)
    r = intent.recognize("那买便宜点的呢", ctx)
    assert r.intent == "purchase"
    assert r.item == "盲盒"
    assert r.is_followup is True


def test_is_uncertain():
    # 闲聊但带消费信号 -> 不确定
    assert intent.is_uncertain(intent.recognize("帮我看看618要不要囤货")) is True
    # 纯问候 -> 确定（不必动用 LLM）
    assert intent.is_uncertain(intent.recognize("你好呀")) is False
    # 已识别出品类的消费 -> 确定
    assert intent.is_uncertain(intent.recognize("我好想花800块买个盲盒")) is False


def test_apply_slots_overrides_uncertain():
    base = intent.recognize("帮我看看那块机械表")  # 未知品类
    slots = {"intent": "purchase", "item": "机械表", "price": 2000}
    r = intent.apply_slots(base, slots)
    assert r.intent == "purchase"
    assert r.item == "机械表"
    assert r.price == 2000


def test_apply_slots_ignores_invalid_intent():
    base = intent.recognize("随便聊聊")
    r = intent.apply_slots(base, {"intent": "nonsense"})
    assert r.intent == base.intent
