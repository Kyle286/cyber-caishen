from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import agent, db
from app.main import app


@pytest.fixture()
def client(monkeypatch, tmp_path):
    # 隔离数据库到临时文件，并强制 LLM 走本地回退（避免测试依赖网络）
    path = str(tmp_path / "test.db")
    monkeypatch.setattr(db, "settings", SimpleNamespace(db_path=path))
    monkeypatch.setattr(agent.llm, "chat", lambda *a, **k: None)
    db.init_db(path)
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert "llm_enabled" in r.json()


def test_goal_crud_and_progress(client):
    r = client.post(
        "/api/goal",
        json={"name": "iPhone", "target_amount": 8000, "monthly_saving": 2000, "saved_amount": 2000},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["goal"]["name"] == "iPhone"
    assert data["progress_ratio"] == 0.25

    r2 = client.get("/api/goal")
    assert r2.json()["goal"]["target_amount"] == 8000

    r3 = client.post("/api/goal/deposit", json={"amount": 2000})
    assert r3.json()["goal"]["saved_amount"] == 4000
    assert r3.json()["progress_ratio"] == 0.5


def test_deposit_rejects_non_positive(client):
    client.post("/api/goal", json={"name": "x", "target_amount": 100})
    r = client.post("/api/goal/deposit", json={"amount": -5})
    assert r.status_code == 422  # Pydantic gt=0 校验


def test_chat_purchase_flow(client):
    client.post("/api/goal", json={"name": "iPhone", "target_amount": 6000, "monthly_saving": 2000})
    r = client.post("/api/chat", json={"message": "我好想花800块买个盲盒", "role": "bestie"})
    assert r.status_code == 200
    data = r.json()
    assert data["intent"] == "purchase"
    assert data["verdict"] == "discourage"
    assert data["price"]["lowest_price"] == 199
    assert len(data["cot_steps"]) >= 5
    assert data["impulse"]["score"] > 0
    assert data["llm_used"] is False


def test_decision_resisted_deposits_to_goal(client):
    client.post("/api/goal", json={"name": "iPhone", "target_amount": 6000, "saved_amount": 1000})
    r = client.post("/api/decision", json={"item": "盲盒", "price": 800, "action": "resisted", "role": "bestie"})
    assert r.status_code == 200
    body = r.json()
    assert body["stats"]["resisted_count"] == 1
    assert body["stats"]["total_saved"] == 800
    # 忍住的钱进了目标：1000 + 800
    assert body["progress"]["goal"]["saved_amount"] == 1800


def test_stats_counts_bought_and_resisted(client):
    client.post("/api/goal", json={"name": "x", "target_amount": 5000})
    client.post("/api/decision", json={"item": "a", "price": 100, "action": "resisted"})
    client.post("/api/decision", json={"item": "b", "price": 50, "action": "bought"})
    s = client.get("/api/stats").json()
    assert s["resisted_count"] == 1
    assert s["bought_count"] == 1
    assert s["total_saved"] == 100
