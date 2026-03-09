# 当前状态快照

本快照基于 2026-03-09 的仓库状态编写。

## 后端

- 框架：FastAPI
- 入口：`backend/app/main.py`
- 路由聚合：`backend/app/api/api.py`
- 当前激活路由：
  - `backend/app/api/routes/competitions.py`
  - `backend/app/api/routes/research_runtime.py`
  - `backend/app/api/routes/agent_tasks.py`
- 核心运行时 service：`backend/app/services/research_runtime_service.py`
- ledger 仓储：`backend/app/repositories/ledger_repository.py`
- 当前真实链路：
  - `FastAPI route -> ResearchRuntimeService -> mock manager / Ark-only Agents SDK runtime -> LedgerRepository`

## Runtime 现状

- 当前主任务类型：
  - `competition_recommendation`
  - `competition_eligibility_check`
  - `competition_timeline_plan`
- legacy `research_plan` 仍保兼容
- 当前已有显式状态机：
  - `received`
  - `planning`
  - `retrieving_local_context`
  - `reasoning`
  - `validating_output`
  - `persisting_artifacts`
  - `completed`
  - `failed`
  - `awaiting_review`
- 当前 ledger 已记录：
  - `events`
  - `artifacts`
  - `raw_outputs`
  - `repaired_outputs`
  - `validation_errors`
  - `parse_errors`
  - `completed_states`
  - `error_stage`
  - `fallback_reason`
  - `elapsed_ms`

## 数据与 grounding

- 原始竞赛数据：`backend/data/competitions.json`
- 领域增强数据：
  - `backend/data/competitions_enriched.json`
  - `backend/data/eligibility_rules.json`
  - `backend/data/recommendation_rubric.json`
  - `backend/data/timeline_templates.json`
- 当前不使用联网检索、RAG、向量数据库

## API 现状

### 保持不变的竞赛接口

- `GET /api/competitions`
- `GET /api/competitions/{id}`

### 新增统一任务接口

- `POST /api/agent/tasks`
- `GET /api/agent/tasks/{run_id}`
- `GET /api/agent/tasks/{run_id}/events`
- `GET /api/agent/tasks/{run_id}/artifacts`

### 旧兼容接口

- `POST /api/research-runtime/run`
- `GET /api/research-runtime/ledger/{ledger_id}`

## 前端

- 框架：Vue 3 + Vite
- 当前页面仍以竞赛列表与详情展示为主
- 当前未改造现有页面
- 已新增接入准备：
  - `frontend/src/api/agent.ts`
  - `frontend/src/types/agent.ts`
  - `frontend/src/features/agent/README.md`

## 测试与评测

- 后端单元测试位于 `backend/app/tests/`
- 当前已有 Phase 4A/4B 相关测试：
  - task flows
  - output repair
  - ledger state machine
  - agent task routes
  - eval regression
  - competitions routes
  - research runtime compatibility
- 本地评测数据位于 `backend/data/evals/`
- 本地评测脚本：`backend/scripts/run_eval.py`
