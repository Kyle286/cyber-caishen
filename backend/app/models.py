"""Pydantic 请求/响应模型。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["caishen", "bestie"]
IntentType = Literal["purchase", "set_goal", "query_progress", "resist", "chitchat"]
Verdict = Literal["discourage", "encourage", "neutral"]
DecisionAction = Literal["resisted", "bought"]


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
    save_if_lowest: Optional[float] = None  # 若买到底价可省的钱
    comment: str


class GoalImpact(BaseModel):
    """该笔消费对攒钱目标的影响。"""
    has_goal: bool
    goal_impact_ratio: Optional[float] = None  # 消费金额占目标的比例
    delay_days: Optional[int] = None  # 会让目标延后的天数
    note: str


class ImpulseScore(BaseModel):
    """冲动指数（0-100，越高越该忍住）。"""
    score: int
    level: str  # 理智 / 犹豫 / 冲动 / 剁手警告
    reasons: list[str] = []


class CotStep(BaseModel):
    label: str
    detail: str


class ChatTurn(BaseModel):
    """多轮历史中的一条消息。"""
    sender: Literal["user", "agent"]
    text: str


class ChatContext(BaseModel):
    """上下文补槽：上一笔被讨论的消费，用于'那买便宜点的呢'这类追问。"""
    last_item: Optional[str] = None
    last_price: Optional[float] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    role: Role = "caishen"
    history: list[ChatTurn] = Field(default_factory=list)
    context: Optional[ChatContext] = None
    model: Optional[str] = None  # 前端选择的模型；非法/缺省时后端回退默认


class ChatResponse(BaseModel):
    reply: str
    role: Role
    intent: IntentType
    verdict: Optional[Verdict] = None
    price: Optional[PriceInfo] = None
    impact: Optional[GoalImpact] = None
    impulse: Optional[ImpulseScore] = None
    opportunity_cost: list[str] = []
    cot_steps: list[CotStep] = []
    context: Optional[ChatContext] = None  # 回传更新后的上下文供前端保存
    llm_used: bool = False


class DecisionIn(BaseModel):
    item: Optional[str] = None
    price: float = Field(..., gt=0)
    action: DecisionAction
    role: Role = "caishen"


class Stats(BaseModel):
    resisted_count: int = 0
    bought_count: int = 0
    total_avoided: float = 0.0  # 累计"免于冲动消费"的金额（非实际已攒，需用户主动存入）
