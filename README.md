# CompAssistant

CompAssistant 当前是一个以大学生竞赛助手为核心的前后端项目。

仓库仍然保留原有的 `competitions.json` 数据源和 `competitions` API，同时已经补齐一套可本地运行的 Agent Runtime，用于把竞赛助手能力包装成可解释、可恢复、可轮询的后端契约层。

## 当前能力

- 竞赛列表与详情接口仍然可用：`/api/competitions`、`/api/competitions/{id}`
- Ark-only + `chat_completions` 真实模式仍然保留
- mock runtime 仍然保留，并作为本地稳定回归基线
- 当前主任务类型收敛为 3 类：
  - `competition_recommendation`
  - `competition_eligibility_check`
  - `competition_timeline_plan`
- legacy `research_plan` 路径仍保兼容，但不再作为前端主接入路径
- 新增统一轮询式任务 API：
  - `POST /api/agent/tasks`
  - `GET /api/agent/tasks/{run_id}`
  - `GET /api/agent/tasks/{run_id}/events`
  - `GET /api/agent/tasks/{run_id}/artifacts`

## 后端运行时概览

当前真实链路为：

`FastAPI route -> ResearchRuntimeService -> mock manager / Ark-only Agents SDK runtime -> LedgerRepository`

Phase 4A 已经完成的核心增强包括：

- 3 类竞赛任务主路径
- 显式 run state machine
- ledger events / artifacts / raw / repaired outputs
- output repair / extraction / validation 三段式
- 本地领域数据增强与工具层 grounding

Phase 4B 在此基础上新增：

- 面向前端轮询的 task/run API
- 薄 DTO 与前端 types 对齐
- 本地 evaluation dataset 与回归脚本
- 前端最小 API client / types 占位

## 目录

```text
CompAssistant/
├─ backend/
│  ├─ app/
│  │  ├─ agents/
│  │  ├─ api/routes/
│  │  ├─ repositories/
│  │  ├─ schemas/
│  │  ├─ services/
│  │  ├─ tests/
│  │  └─ tools/
│  ├─ data/
│  │  ├─ competitions.json
│  │  ├─ competitions_enriched.json
│  │  ├─ eligibility_rules.json
│  │  ├─ recommendation_rubric.json
│  │  ├─ timeline_templates.json
│  │  └─ evals/
│  └─ scripts/run_eval.py
├─ docs/
└─ frontend/
   └─ src/
      ├─ api/agent.ts
      ├─ types/agent.ts
      └─ features/agent/
```

## 快速开始

### 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 主要 API

### 竞赛数据

- `GET /api/competitions`
- `GET /api/competitions/{id}`

### 新任务 API

- `POST /api/agent/tasks`
- `GET /api/agent/tasks/{run_id}`
- `GET /api/agent/tasks/{run_id}/events`
- `GET /api/agent/tasks/{run_id}/artifacts`

### 旧兼容路由

- `POST /api/research-runtime/run`
- `GET /api/research-runtime/ledger/{ledger_id}`

前端新接入应优先使用 `/api/agent/tasks/*`，不要直接绑定旧 `research-runtime` 路由。

## 本地回归

### 运行后端测试

```bash
backend\.venv\Scripts\python -m unittest discover -s backend/app/tests
```

### 运行本地评测

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock
```

如需 JSON 输出：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock --json
```

## 文档

- `docs/current-state.md`
- `docs/agent-runtime-overview.md`
- `docs/task-types.md`
- `docs/ledger-state-machine.md`
- `docs/frontend-integration.md`
- `docs/evaluation.md`

## 当前边界

- 不引入 WebSearch、RAG、向量数据库、Redis、Celery
- 不重写现有前端页面
- 不替换 Ark-only 主逻辑
- 不删除 mock fallback
