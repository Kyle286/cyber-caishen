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
    assert len(resp.cot_steps) == 4
    assert resp.reply  # 非空


def test_handle_chat_chitchat(temp_db, monkeypatch):
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: None)
    resp = agent.handle_chat("你好", "caishen", db_path=temp_db)
    assert resp.intent == "chitchat"
    assert resp.reply
