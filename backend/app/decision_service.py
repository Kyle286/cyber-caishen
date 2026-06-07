"""消费决策记录服务：打通'反冲动 -> 攒钱'闭环。

用户对一条消费建议可选择"忍住了"或"还是买了"。忍住只记录为"免于冲动消费"，
并不自动计入已攒——因为钱仍在用户账户里。是否把省下的钱真正存进目标，
由用户再做一次明确的存入动作（对应现实中真的转一笔账），口径更干净。
"""
from __future__ import annotations

from typing import Optional

from . import goal_service
from .db import get_conn, now_iso
from .models import GoalProgress, Stats


def record_decision(
    item: Optional[str],
    price: float,
    action: str,
    role: str,
    db_path: Optional[str] = None,
) -> tuple[Stats, GoalProgress]:
    """记录一次决策（不自动存入目标）。返回 (统计, 当前目标进度)。"""
    conn = get_conn(db_path)
    try:
        verdict = "resisted" if action == "resisted" else "bought"
        conn.execute(
            "INSERT INTO decisions (item, price, verdict, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (item, price, verdict, role, now_iso()),
        )
        conn.commit()
    finally:
        conn.close()

    goal = goal_service.get_current_goal(db_path)
    return get_stats(db_path), goal_service.compute_progress(goal)


def get_stats(db_path: Optional[str] = None) -> Stats:
    """统计：劝退次数、购买次数、累计'免于冲动消费'的金额。"""
    conn = get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT "
            "  SUM(CASE WHEN verdict='resisted' THEN 1 ELSE 0 END) AS resisted, "
            "  SUM(CASE WHEN verdict='bought' THEN 1 ELSE 0 END) AS bought, "
            "  SUM(CASE WHEN verdict='resisted' THEN price ELSE 0 END) AS avoided "
            "FROM decisions"
        ).fetchone()
        return Stats(
            resisted_count=int(row["resisted"] or 0),
            bought_count=int(row["bought"] or 0),
            total_avoided=float(row["avoided"] or 0.0),
        )
    finally:
        conn.close()
