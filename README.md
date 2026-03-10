# CompAssistant

CompAssistant 已不再只是一个 `competitions` 列表项目，而是一个同时包含两条能力线的竞赛助手仓库：

- 原有的竞赛列表与详情 API
- 基于 Ark-only runtime 的竞赛任务智能体能力，支持本地 mock fallback

当前主任务类型：

- `competition_recommendation`
- `competition_eligibility_check`
- `competition_timeline_plan`

legacy `research_plan` 仍保兼容，但不再是主演示路径。

## 当前系统能力

- `POST /api/agent/tasks` 支持“创建即返回 `run_id` + `queued`，后台线程继续执行”
- `GET /api/agent/tasks/{run_id}`、`/events`、`/artifacts` 可轮询读取任务状态、事件与结果
- `GET /api/agent/tasks` 支持历史任务列表、筛选与分页
- `retry / cancel / review` 已具备最小控制闭环
- 本地 `run_eval.py` 可运行结构 + 质量混合回归
- 前端已有最小 Agent 面板，支持历史、控制和双模式输入

## 当前前端输入层

Agent 面板现在提供两种输入模式：

- `简洁模式`
  - 面向普通用户
  - 使用自然表单输入
  - 前端自动组装 `objective + payload`
  - 提交前可预览将要发送的 payload
- `高级模式`
  - 面向调试、回归测试和精确构造 case
  - 保留原始 `objective + payload JSON` 编辑入口

重要约束：

- `payload` 仍然是内部 canonical representation
- `Simple Mode` 只是输入适配层，不改变现有 task API
- 附件当前仅支持 `payload.attachments` 元数据预留，不代表已经实现完整多模态推理

## 后端主链路

当前后端真实链路为：

`FastAPI route -> ResearchRuntimeService -> mock manager 或 Ark-only Agents SDK runtime -> LedgerRepository`

保留能力包括：

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

推荐接入的智能体任务 API：

- `POST /api/agent/tasks`
- `GET /api/agent/tasks`
- `GET /api/agent/tasks/{run_id}`
- `GET /api/agent/tasks/{run_id}/events`
- `GET /api/agent/tasks/{run_id}/artifacts`
- `POST /api/agent/tasks/{run_id}/retry`
- `POST /api/agent/tasks/{run_id}/cancel`
- `POST /api/agent/tasks/{run_id}/review`

兼容接口：

- `POST /api/research-runtime/run`
- `GET /api/research-runtime/ledger/{ledger_id}`

前端新接入应优先使用 `/api/agent/tasks/*`。

## 本地数据

受版本控制的基础数据位于 `backend/data/`：

- `competitions.json`
- `competitions_enriched.json`
- `eligibility_rules.json`
- `recommendation_rubric.json`
- `timeline_templates.json`
- `evals/*.json`

运行时 ledger、SQLite、WAL/SHM 等产物不应提交到仓库。

## 启动方式

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

## 相关文档

- `docs/current-state.md`
- `docs/frontend-integration.md`
- `docs/evaluation.md`
- `docs/operator-guide.md`
- `docs/demo-phase5b.md`

## 当前边界

- 不引入 WebSocket、Redis、Celery、消息队列
- 不引入 RAG、向量数据库、联网检索
- 不重写现有 competitions 页面
- 不删除 mock fallback
- 当前附件/多模态仅预留输入元数据，不代表 runtime 已消费
- 当前没有重构 runtime，只是逐步把输入层、控制面和可观测性补齐
