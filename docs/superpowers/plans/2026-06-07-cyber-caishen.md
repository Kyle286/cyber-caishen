# 赛博财神爷 实现计划

> **For agentic workers:** 按任务顺序实现，每个任务完成后即时提交（中文 commit）。

**Goal:** 实现一个反冲动消费与攒钱陪伴 Agent，含 FastAPI 后端与 React 前端，可本地一键演示。

**Architecture:** 后端用 FastAPI 提供意图识别、模拟比价、攒钱进度计算与人格化对话（DeepSeek + 本地兜底）；前端用 React+Vite+TS 提供聊天流、攒钱目标面板与人格切换。SQLite 持久化攒钱目标。

**Tech Stack:** Python/FastAPI/SQLite/httpx/pytest, React/Vite/TypeScript

---

## Task 1: 后端骨架与配置
- Create: `backend/requirements.txt`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/.env.example`
- 配置读取 DeepSeek key、base_url、model；提供默认值

## Task 2: 数据层
- Create: `backend/app/db.py`, `backend/app/models.py`
- SQLite 初始化（goals、decisions 表），Pydantic 模型

## Task 3: 意图识别
- Create: `backend/app/intent.py`, `backend/tests/test_intent.py`
- 抽取物品名、金额、意图类型；TDD

## Task 4: 模拟商品库与比价
- Create: `backend/app/price_db.py`, `backend/tests/test_price_db.py`
- 内置品类库，返回均价/底价/溢价率；TDD

## Task 5: 攒钱目标服务
- Create: `backend/app/goal_service.py`, `backend/tests/test_goal_service.py`
- 进度、消费影响（占比/延后天数）计算；TDD

## Task 6: 人格 Prompt 与 Agent 核心
- Create: `backend/app/prompts.py`, `backend/app/llm.py`, `backend/app/agent.py`, `backend/tests/test_agent.py`
- 组装 CoT、裁决逻辑、LLM 调用与本地回退；TDD（回退路径）

## Task 7: API 路由
- Create: `backend/app/main.py`
- /api/health /api/goal /api/goal/deposit /api/chat

## Task 8: 前端骨架
- Create: Vite React TS 工程，`frontend/package.json` 等

## Task 9: 前端 API 与组件
- Create: api client、ChatPanel、MessageBubble、AnalysisCard、GoalPanel、RoleSwitch

## Task 10: 样式与体验打磨
- 现代化 UI、进度环、响应式

## Task 11: README 与启动脚本
- Create: `README.md`，前后端启动说明，截图占位

## Task 12: 联调与验收
- 端到端验证验收标准
