import os
import tempfile

import pytest

from app import db, goal_service
from app.models import Goal


@pytest.fixture()
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db.init_db(path)
    yield path
    os.remove(path)


def test_upsert_and_get_goal(temp_db):
    g = goal_service.upsert_goal("iPhone", 6000, monthly_saving=1000, db_path=temp_db)
    assert g.name == "iPhone"
    cur = goal_service.get_current_goal(temp_db)
    assert cur is not None
    assert cur.target_amount == 6000


def test_compute_progress(temp_db):
    goal_service.upsert_goal("旅行", 10000, monthly_saving=2000, saved_amount=2500, db_path=temp_db)
    goal = goal_service.get_current_goal(temp_db)
    p = goal_service.compute_progress(goal)
    assert p.progress_ratio == 0.25
    assert p.remaining == 7500
    assert p.months_to_go == 3.8  # round(7500/2000, 1)


def test_compute_impact_with_goal():
    goal = Goal(id=1, name="t", target_amount=10000, saved_amount=0, monthly_saving=3000, created_at="now")
    impact = goal_service.compute_impact(goal, 800)
    assert impact.has_goal
    assert impact.goal_impact_ratio == 0.08
    assert impact.delay_days == 8  # 800 / (3000/30=100) = 8 天


def test_compute_impact_no_goal():
    impact = goal_service.compute_impact(None, 800)
    assert impact.has_goal is False


def test_deposit(temp_db):
    goal_service.upsert_goal("车", 50000, saved_amount=1000, db_path=temp_db)
    g = goal_service.deposit(500, temp_db)
    assert g.saved_amount == 1500
