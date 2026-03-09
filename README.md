# CompAssistant

CompAssistant 现在不再只是一个 `competitions` 列表项目，而是一个同时包含以下两条能力线的竞赛助手仓库：

- 原有的竞赛列表与详情 API
- 面向三类竞赛任务的 Ark-only agent runtime，以及本地 mock fallback

当前主任务类型：

- `competition_recommendation`
- `competition_eligibility_check`
- `competition_timeline_plan`

legacy `research_plan` 仍保兼容，但不再是推荐的主接入路径。

## 当前系统能力

- `POST /api/agent/tasks` 支持“创建即返回 `run_id` + `queued`，后台线程继续执行”
- `GET /api/agent/tasks/{run_id}` 可轮询任务状态
- `GET /api/agent/tasks/{run_id}/events` 可读取事件时间线
- `GET /api/agent/tasks/{run_id}/artifacts` 可读取结构化结果
- `GET /api/agent/tasks` 可查询历史任务、筛选和分页
- `POST /api/agent/tasks/{run_id}/retry` 支持最小重试闭环
- `POST /api/agent/tasks/{run_id}/cancel` 支持最小取消闭环
- `POST /api/agent/tasks/{run_id}/review` 支持最小审核动作
- 前端已提供最小 Agent 面板，可创建任务、轮询状态、查看历史、执行控制动作

## 运行链路

当前后端主链路：

`FastAPI route -> ResearchRuntimeService -> mock manager 或 Ark-only Agents SDK runtime -> LedgerRepository`

这条链路保留了：

- Ark-only + `chat_completions`
- mock fallback
- ledger 状态机
- events / artifacts
- output repair / validation
- 本地领域数据 grounding

## API

竞赛 API：

- `GET /api/competitions`
- `GET /api/competitions/{id}`

推荐的智能体任务 API：

- `POST /api/agent/tasks`
- `GET /api/agent/tasks`
- `GET /api/agent/tasks/{run_id}`
- `GET /api/agent/tasks/{run_id}/events`
- `GET /api/agent/tasks/{run_id}/artifacts`
- `POST /api/agent/tasks/{run_id}/retry`
- `POST /api/agent/tasks/{run_id}/cancel`
- `POST /api/agent/tasks/{run_id}/review`

旧兼容接口：

- `POST /api/research-runtime/run`
- `GET /api/research-runtime/ledger/{ledger_id}`

新前端接入应优先使用 `/api/agent/tasks/*`。

## 前端

前端侧栏现在包含一个最小 Agent 面板入口：

- `竞赛列表`
- `使用说明`
- `智能体面板`

Agent 面板支持：

- 选择任务类型
- 输入 objective 和 payload JSON
- 提交任务并立刻拿到 `run_id`
- 轮询状态和事件
- 查看 artifacts
- 查看历史任务
- 对当前任务执行 retry / cancel / review

## 本地数据

受版本控制的基础数据位于 `backend/data/`：

- `competitions.json`
- `competitions_enriched.json`
- `eligibility_rules.json`
- `recommendation_rubric.json`
- `timeline_templates.json`
- `evals/*.json`

运行时 ledger、SQLite、WAL/SHM 等产物应保持忽略，不提交到仓库。

## 本地启动

后端：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 测试与评测

后端测试：

```bash
backend\.venv\Scripts\python -m unittest discover -s backend/app/tests
```

前端构建校验：

```bash
cd frontend
npm run build
```

本地评测：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock
```

JSON 报告：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock --json
```

## 文档

- `docs/frontend-integration.md`
- `docs/evaluation.md`
- `docs/operator-guide.md`
- `docs/demo-phase5a.md`
- `docs/demo-phase5b.md`

## 当前边界

- 不引入 WebSocket、Redis、Celery、消息队列
- 不引入 RAG、向量数据库、联网检索
- 不重写现有 competitions 页面
- 不删除 mock fallback
- Phase 5B 的控制接口仍是最小闭环，不是完整审批系统
