import os
import tempfile

import pytest

from app import agent, goal_service, db
from app.models import GoalImpact, PriceInfo


@pytest.fixture()
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db.init_db(path)
    yield path
    os.remove(path)


def _price(overprice):
    return PriceInfo(item="盲盒", category="盲盒", user_price=800, avg_price=320,
                     lowest_price=199, highest_price=999, overprice_ratio=overprice, comment="x")


def test_verdict_discourage_on_high_overprice():
    impact = GoalImpact(has_goal=True, goal_impact_ratio=0.02, delay_days=2, note="x")
    assert agent.decide_verdict(_price(1.5), impact) == "discourage"


def test_verdict_discourage_on_high_goal_ratio():
    impact = GoalImpact(has_goal=True, goal_impact_ratio=0.2, delay_days=2, note="x")
    assert agent.decide_verdict(_price(0.1), impact) == "discourage"


def test_verdict_encourage_on_bargain():
    impact = GoalImpact(has_goal=True, goal_impact_ratio=0.01, delay_days=2, note="x")
    assert agent.decide_verdict(_price(0.1), impact) == "encourage"


def test_handle_chat_purchase_fallback(temp_db, monkeypatch):
    # 强制 LLM 返回 None，走本地回退
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: None)
    goal_service.upsert_goal("iPhone", 6000, monthly_saving=2000, db_path=temp_db)
    resp = agent.handle_chat("我好想花800块买个盲盒", "bestie", db_path=temp_db)
    assert resp.intent == "purchase"
    assert resp.price is not None
    assert resp.verdict is not None
    assert resp.llm_used is False
    assert len(resp.cot_steps) >= 5  # 意图/比价/目标/机会成本/冲动指数/裁决
    assert resp.impulse is not None
    assert resp.opportunity_cost
    assert resp.reply  # 非空


def test_handle_chat_chitchat(temp_db, monkeypatch):
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: None)
    resp = agent.handle_chat("你好", "caishen", db_path=temp_db)
    assert resp.intent == "chitchat"
    assert resp.reply


def test_verdict_neutral_when_no_price():
    # 无价格时不应轻率鼓励
    impact = GoalImpact(has_goal=True, goal_impact_ratio=0.01, delay_days=1, note="x")
    price_no_value = PriceInfo(item="盲盒", category="盲盒", user_price=None, avg_price=320,
                               lowest_price=199, highest_price=999, overprice_ratio=None, comment="x")
    assert agent.decide_verdict(price_no_value, impact) == "neutral"
    assert agent.decide_verdict(None, impact) == "neutral"


def test_personas_produce_different_text(temp_db, monkeypatch):
    # 验收 #4：两种人格回复风格应明显不同（此处校验本地兜底文案不一致）
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: None)
    goal_service.upsert_goal("iPhone", 6000, monthly_saving=2000, db_path=temp_db)
    caishen = agent.handle_chat("我好想花800块买个盲盒", "caishen", db_path=temp_db)
    bestie = agent.handle_chat("我好想花800块买个盲盒", "bestie", db_path=temp_db)
    assert caishen.reply != bestie.reply
    assert "财神" in caishen.reply
    assert "姐妹" in bestie.reply


def test_handle_chat_set_goal_branch(temp_db, monkeypatch):
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: None)
    resp = agent.handle_chat("我想攒钱买手机，目标6000", "caishen", db_path=temp_db)
    assert resp.intent == "set_goal"
    assert resp.reply


def test_handle_chat_query_progress_branch(temp_db, monkeypatch):
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: None)
    goal_service.upsert_goal("旅行", 10000, saved_amount=2500, monthly_saving=2000, db_path=temp_db)
    resp = agent.handle_chat("我的攒钱进度怎么样了", "caishen", db_path=temp_db)
    assert resp.intent == "query_progress"
    assert resp.impact is not None and resp.impact.has_goal
    assert "25" in resp.reply or "进度" in resp.reply


def test_handle_chat_purchase_without_price(temp_db, monkeypatch):
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: None)
    resp = agent.handle_chat("我想买个盲盒", "bestie", db_path=temp_db)
    assert resp.intent == "purchase"
    assert resp.verdict == "neutral"  # 无价格 -> 理性提醒


def test_slot_fallback_when_uncertain(temp_db, monkeypatch):
    # 未知品类商品，规则不确定 -> 用 LLM 抽槽补全
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: None)
    monkeypatch.setattr(agent.llm, "extract_slots", lambda *a, **k: {"intent": "purchase", "item": "机械表", "price": 3000})
    resp = agent.handle_chat("帮我看看那块3000的机械表", "caishen", db_path=temp_db)
    assert resp.intent == "purchase"
    assert resp.price is not None
    assert resp.price.user_price == 3000


def test_stream_chat_yields_delta_then_done_with_analysis(temp_db, monkeypatch):
    monkeypatch.setattr(agent.llm, "extract_slots", lambda *a, **k: None)
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: None)  # 补充建议走规则兜底
    monkeypatch.setattr(agent.llm, "chat_stream", lambda *a, **k: iter(["姐妹", "醒醒"]))
    goal_service.upsert_goal("iPhone", 6000, monthly_saving=2000, db_path=temp_db)
    events = list(agent.stream_chat("我好想花800块买个盲盒", "bestie", db_path=temp_db))
    assert events[0]["type"] == "delta"
    deltas = [e["text"] for e in events if e["type"] == "delta"]
    assert "".join(deltas) == "姐妹醒醒"
    done = events[-1]
    assert done["type"] == "done"
    assert done["llm_used"] is True
    assert done["data"]["intent"] == "purchase"
    assert done["data"]["verdict"] == "discourage"
    assert len(done["data"]["suggestions"]) >= 1


def test_stream_chat_fallback_when_no_stream(temp_db, monkeypatch):
    monkeypatch.setattr(agent.llm, "extract_slots", lambda *a, **k: None)
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: None)
    monkeypatch.setattr(agent.llm, "chat_stream", lambda *a, **k: iter([]))  # 无产出
    events = list(agent.stream_chat("我好想花800块买个盲盒", "caishen", db_path=temp_db))
    done = events[-1]
    assert done["type"] == "done"
    assert done["llm_used"] is False
    assert done["data"]["intent"] == "purchase"
    deltas = [e for e in events if e["type"] == "delta"]
    assert len(deltas) == 1 and deltas[0]["text"]  # 兜底文案
