# 赛博财神爷 (cyber-caishen) 设计文档

> 反冲动消费与攒钱陪伴 Agent。用户输入想买的东西，Agent 化身"赛博财神"或"毒舌闺蜜"，
> 通过模拟比价 + 攒钱目标进度计算，给出"劝退/鼓励"的人格化裁决。

## 1. 目标与背景

年轻人"该省省、该花花"，容易在直播间冲动消费，又渴望有目标地攒钱。
本项目是一个理财陪伴 Agent 的 PoC，核心考察：

- 角色扮演（System Prompt 精准控制）
- 意图识别
- 简单数据计算与逻辑链推理（CoT）
- 产品交互设计

## 2. 核心体验

聊天式界面。用户说"我好想花 800 块买个盲盒"，Agent 完成一条**可见的推理链**：

1. **意图识别**：解析出 `物品=盲盒`、`价格=800`、`意图=想消费`
2. **模拟比价**：查内置商品库，给出同类底价（盲盒均价 ¥320、最低 ¥199），算出溢价率
3. **攒钱目标进度**：这 800 元 = 攒钱目标的 X%，会让目标延后 N 天
4. **角色裁决**：财神（温暖鼓励）/ 毒舌闺蜜（犀利劝退）输出结论，带表情与金句

UI 三区：
- 左侧：攒钱目标面板（设目标 / 进度环 / 这笔消费的影响）
- 中间：聊天流（气泡 + 结构化卡片）
- 顶部：人格切换开关（财神 / 毒舌闺蜜）

比价与裁决以**结构化卡片**展示，而非纯文字。

## 3. 架构

### 后端 FastAPI (Python)

| 文件 | 职责 |
|------|------|
| `backend/app/main.py` | FastAPI 应用、CORS、路由挂载 |
| `backend/app/db.py` | SQLite 初始化与连接 |
| `backend/app/models.py` | Pydantic 请求/响应模型 |
| `backend/app/intent.py` | 意图识别：抽取物品名、金额、意图类型 |
| `backend/app/price_db.py` | 内置模拟商品库 + 同类比价查询 |
| `backend/app/goal_service.py` | 攒钱目标 CRUD 与进度/影响计算 |
| `backend/app/agent.py` | 核心：组装 CoT 上下文 → 调 LLM → 失败回退本地模板 |
| `backend/app/llm.py` | DeepSeek 客户端封装，异常返回 None 触发回退 |
| `backend/app/prompts.py` | 两套人格 System Prompt |
| `backend/app/config.py` | 读取 `.env` 配置 |

接口：
- `GET  /api/health` — 健康检查
- `GET  /api/goal` — 获取当前攒钱目标与进度
- `POST /api/goal` — 创建/更新攒钱目标
- `POST /api/goal/deposit` — 手动存入（推进进度，演示用）
- `POST /api/chat` — 核心对话，返回回复 + 结构化分析

### 前端 React + Vite + TypeScript

| 组件 | 职责 |
|------|------|
| `App.tsx` | 布局、全局状态 |
| `components/ChatPanel.tsx` | 聊天流 + 输入框 |
| `components/MessageBubble.tsx` | 气泡渲染 |
| `components/AnalysisCard.tsx` | 比价卡 / 裁决卡 / CoT 步骤 |
| `components/GoalPanel.tsx` | 攒钱目标设置 + 进度环 |
| `components/RoleSwitch.tsx` | 人格切换 |
| `api/client.ts` | 后端 API 封装 |

## 4. 数据流

```
前端 {message, role, goal_id}
  -> 意图识别 (intent.py)
  -> 比价 (price_db.py) + 目标进度/影响 (goal_service.py)
  -> 组装结构化 analysis + CoT steps
  -> LLM 人格化文案 (agent.py -> llm.py, 失败回退 prompts 模板)
  -> 返回 {reply, role, intent, analysis, cot_steps, verdict}
前端渲染聊天气泡 + 结构化卡片, 刷新进度环
```

## 5. 数据模型 (SQLite)

```sql
CREATE TABLE goals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  target_amount REAL NOT NULL,
  saved_amount REAL NOT NULL DEFAULT 0,
  monthly_saving REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item TEXT,
  price REAL,
  verdict TEXT,        -- 'discourage' | 'encourage' | 'neutral'
  role TEXT,           -- 'caishen' | 'bestie'
  created_at TEXT NOT NULL
);
```

## 6. 意图类型

- `purchase` 想消费（含物品+金额）
- `set_goal` 设定攒钱目标
- `query_progress` 查询攒钱进度
- `chitchat` 闲聊/其他

## 7. 裁决逻辑（本地规则，LLM 在此基础上润色）

输入信号：溢价率 `overprice_ratio`、消费占目标比例 `goal_impact_ratio`、延后天数 `delay_days`。

- 溢价率高 或 占目标比例高（>10%）或 延后天数多 → `discourage`（劝退）
- 价格合理且占比低（<3%）→ `encourage`（鼓励/适度满足）
- 介于之间 → `neutral`（提醒理性）

## 8. 容错与降级

- LLM 无 key / 超时 / 报错 → 本地规则模板生成人格化回复，保证演示永远可用
- 意图无法解析金额 → Agent 反问澄清
- 攒钱目标未设置 → 引导先设目标
- API key 通过 `.env` 注入，`.env` 不进 git，提供 `.env.example`

## 9. 验收标准

1. 本地一键启动（后端 + 前端），README 有清晰步骤
2. 输入消费意图能正确抽取物品+金额，展示比价卡（含底价/溢价率）
3. 展示攒钱目标进度环，并算出该笔消费对目标的影响（延后天数/占比）
4. 财神 vs 毒舌闺蜜两种人格输出风格明显不同（System Prompt 控制）
5. CoT 推理步骤可见（4 步链路）
6. 断网 / 无 key 时回退本地模板仍可演示
7. UI 美观、交互流畅、可现场演示
8. 后端有单元测试覆盖意图识别、比价、进度计算、裁决逻辑

## 10. 技术栈

- 后端：Python 3.10+、FastAPI、Uvicorn、SQLite、httpx、pydantic、pytest
- 前端：React 18、Vite、TypeScript
- LLM：DeepSeek（OpenAI 兼容接口），本地规则兜底
