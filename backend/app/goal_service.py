"""攒钱目标服务：CRUD + 进度/消费影响计算。"""
from __future__ import annotations

import math
from typing import Optional

from .db import get_conn, now_iso
from .models import Goal, GoalImpact, GoalProgress


def get_current_goal(db_path: Optional[str] = None) -> Optional[Goal]:
    """取最新的一个攒钱目标（PoC 简化为单目标）。"""
    conn = get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM goals ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return _row_to_goal(row) if row else None
    finally:
        conn.close()


def upsert_goal(
    name: str,
    target_amount: float,
    monthly_saving: float = 0,
    saved_amount: float = 0,
    db_path: Optional[str] = None,
) -> Goal:
    """创建新的攒钱目标。"""
    conn = get_conn(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO goals (name, target_amount, saved_amount, monthly_saving, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, target_amount, saved_amount, monthly_saving, now_iso()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM goals WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_goal(row)
    finally:
        conn.close()


def deposit(amount: float, db_path: Optional[str] = None) -> Optional[Goal]:
    """向当前目标存入金额。"""
    goal = get_current_goal(db_path)
    if not goal:
        return None
    conn = get_conn(db_path)
    try:
        new_saved = goal.saved_amount + amount
        conn.execute("UPDATE goals SET saved_amount = ? WHERE id = ?", (new_saved, goal.id))
        conn.commit()
        row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal.id,)).fetchone()
        return _row_to_goal(row)
    finally:
        conn.close()


def compute_progress(goal: Optional[Goal]) -> GoalProgress:
    """计算攒钱进度。"""
    if not goal:
        return GoalProgress()
    remaining = max(goal.target_amount - goal.saved_amount, 0.0)
    ratio = 0.0
    if goal.target_amount > 0:
        ratio = round(min(goal.saved_amount / goal.target_amount, 1.0), 4)
    months = None
    if goal.monthly_saving > 0:
        months = round(remaining / goal.monthly_saving, 1)
    return GoalProgress(goal=goal, progress_ratio=ratio, remaining=remaining, months_to_go=months)


def compute_impact(goal: Optional[Goal], price: Optional[float]) -> GoalImpact:
    """计算一笔消费对攒钱目标的影响。"""
    if not goal:
        return GoalImpact(has_goal=False, note="你还没设定攒钱目标，先定个小目标吧～")
    if price is None:
        return GoalImpact(has_goal=True, note="没识别到具体金额，告诉我多少钱我帮你算。")

    impact_ratio = round(price / goal.target_amount, 4) if goal.target_amount > 0 else None

    delay_days = None
    if goal.monthly_saving > 0:
        # 这笔钱相当于多攒多少天（按每月攒钱额折算成日攒钱额）
        daily = goal.monthly_saving / 30.0
        delay_days = int(math.ceil(price / daily)) if daily > 0 else None

    note = _impact_note(impact_ratio, delay_days, price)
    return GoalImpact(
        has_goal=True,
        goal_impact_ratio=impact_ratio,
        delay_days=delay_days,
        note=note,
    )


def _impact_note(ratio, delay_days, price) -> str:
    parts = [f"这笔 ¥{price:.0f} 的消费"]
    if ratio is not None:
        parts.append(f"相当于攒钱目标的 {ratio*100:.1f}%")
    if delay_days is not None:
        parts.append(f"会让你的目标延后约 {delay_days} 天")
    return "，".join(parts) + "。"


def _row_to_goal(row) -> Goal:
    return Goal(
        id=row["id"],
        name=row["name"],
        target_amount=row["target_amount"],
        saved_amount=row["saved_amount"],
        monthly_saving=row["monthly_saving"],
        created_at=row["created_at"],
    )
