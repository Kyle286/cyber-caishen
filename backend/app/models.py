"""Pydantic 请求/响应模型。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["caishen", "bestie"]
IntentType = Literal["purchase", "set_goal", "query_progress", "chitchat"]
Verdict = Literal["discourage", "encourage", "neutral"]


class GoalIn(BaseModel):
    name: str = Field(..., description="攒钱目标名称，如 'iPhone 16'")
    target_amount: float = Field(..., gt=0, description="目标金额")
    monthly_saving: float = Field(0, ge=0, description="每月可攒金额")
    saved_amount: float = Field(0, ge=0, description="已攒金额")


class Goal(BaseModel):
    id: int
    name: str
    target_amount: float
    saved_amount: float
    monthly_saving: float
    created_at: str


class GoalProgress(BaseModel):
    goal: Optional[Goal] = None
    progress_ratio: float = 0.0
    remaining: float = 0.0
    months_to_go: Optional[float] = None


class DepositIn(BaseModel):
    amount: float = Field(..., gt=0)


class PriceInfo(BaseModel):
    """比价结果。"""
    item: str
    category: str
    user_price: Optional[float] = None
    avg_price: float
    lowest_price: float
    highest_price: float
    overprice_ratio: Optional[float] = None  # 用户价格相对底价的溢价率
    comment: str


class GoalImpact(BaseModel):
    """该笔消费对攒钱目标的影响。"""
    has_goal: bool
    goal_impact_ratio: Optional[float] = None  # 消费金额占目标的比例
    delay_days: Optional[int] = None  # 会让目标延后的天数
    note: str


class CotStep(BaseModel):
    label: str
    detail: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    role: Role = "caishen"


class ChatResponse(BaseModel):
    reply: str
    role: Role
    intent: IntentType
    verdict: Optional[Verdict] = None
    price: Optional[PriceInfo] = None
    impact: Optional[GoalImpact] = None
    cot_steps: list[CotStep] = []
    llm_used: bool = False
