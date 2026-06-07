"""FastAPI 应用入口与路由。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import agent, goal_service
from .db import init_db
from .models import (
    ChatRequest,
    ChatResponse,
    DepositIn,
    GoalIn,
    GoalProgress,
)

app = FastAPI(title="赛博财神爷 API", version="1.0.0", description="反冲动消费与攒钱陪伴 Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


init_db()


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    from .config import settings
    return {"status": "ok", "llm_enabled": settings.llm_enabled, "model": settings.deepseek_model}


@app.get("/api/goal", response_model=GoalProgress)
def get_goal() -> GoalProgress:
    goal = goal_service.get_current_goal()
    return goal_service.compute_progress(goal)


@app.post("/api/goal", response_model=GoalProgress)
def set_goal(body: GoalIn) -> GoalProgress:
    goal = goal_service.upsert_goal(
        name=body.name,
        target_amount=body.target_amount,
        monthly_saving=body.monthly_saving,
        saved_amount=body.saved_amount,
    )
    return goal_service.compute_progress(goal)


@app.post("/api/goal/deposit", response_model=GoalProgress)
def deposit_goal(body: DepositIn) -> GoalProgress:
    goal = goal_service.deposit(body.amount)
    return goal_service.compute_progress(goal)


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    return agent.handle_chat(body.message, body.role)
