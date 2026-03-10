# CompAssistant

CompAssistant 现在不再只是一个 `competitions` 列表项目，而是一个保留原有竞赛数据能力、同时补齐最小 Agent 演示闭环的仓库。

当前已经落到 Phase 5D-lite，核心能力包括：

- 原有 `competitions` 列表与详情 API
- Ark-only agent runtime，保留本地 mock fallback
- 三类主任务：
  - `competition_recommendation`
  - `competition_eligibility_check`
  - `competition_timeline_plan`
- `task / run / events / artifacts` API
- 历史列表、`retry / cancel / review`
- Simple / Advanced 双模式输入
- 本地 `run_eval.py` 回归
- 最小浏览器级 Playwright smoke

`payload` 仍然是内部 canonical representation。Simple Mode 只是输入适配层，不改变现有 task API；Advanced Mode 继续保留给调试、演示和评测使用。

## 当前主链路

后端真实链路：

`FastAPI route -> ResearchRuntimeService -> mock manager / Ark-only Agents SDK runtime -> LedgerRepository`

保持不变的边界：

- 不引入新的 agent runtime 框架
- 不引入 WebSocket / Redis / Celery / RAG / 向量数据库
- 不破坏现有 `competitions` API
- 不删除 mock fallback

## API

竞赛 API：

- `GET /api/competitions`
- `GET /api/competitions/{id}`

推荐前端接入的 Agent API：

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

## 前端输入层

Agent 面板位于侧栏“智能体面板”入口，当前支持：

- 简洁模式
  - 使用自然表单输入
  - 自动组装 `objective + payload`
  - 提交前展示 payload 预览
  - `eligibility / timeline` 支持竞赛名称搜索建议，最终仍提交 canonical `competition_id`
- 高级模式
  - 保留原始 `objective + payload JSON` 编辑器
  - 适合调试、回归测试和精确构造 case

附件当前只作为 `payload.attachments` 元数据入口，不代表已经实现完整多模态消费链路。

## 浏览器级 smoke

前端新增了最小 Playwright smoke，覆盖一条 recommendation happy path：

- 打开 Agent 面板
- 使用 Simple Mode 填表
- 查看 payload 预览
- 切到 Advanced Mode 确认 JSON 仍可见
- 提交任务并轮询结果
- 查看事件时间线、artifacts、最近任务
- 执行一次 `retry`
- 返回 `competitions` 页面确认未受影响

相关文件：

- `frontend/playwright.config.ts`
- `frontend/e2e/agent-panel.spec.ts`
- `frontend/e2e/fixtures/agent-demo-cases.json`

## 运行方式

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

后端必要回归：

```bash
backend\.venv\Scripts\python -m unittest \
  backend.app.tests.test_agent_task_routes \
  backend.app.tests.test_agent_task_history_routes \
  backend.app.tests.test_agent_task_control_routes \
  backend.app.tests.test_competitions_routes
```

本地评测：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock
```

前端构建：

```bash
cd frontend
npm run build
```

浏览器 smoke：

```bash
cd frontend
npm run test:e2e:install
npm run test:e2e
```

## 文档

- `docs/current-state.md`
- `docs/frontend-integration.md`
- `docs/evaluation.md`
- `docs/operator-guide.md`
- `docs/demo-phase5c-mini.md`

## 当前限制

- 本轮没有重构 runtime
- 后台执行仍然是进程内线程池
- attachments 仍只是元数据入口，不是完整多模态能力
- 浏览器级 smoke 目前只覆盖 1 条 happy path
- `competitions` 页面与 API 保持兼容，未被本轮改动破坏
