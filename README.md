# CompAssistant

## Phase 5G Update

### Phase 5G note

This repository is now beyond Phase 5F and includes a focused Phase 5G hardening pass.

What changed in this pass:

- `recommendation-003` is no longer primarily blocked by the old `Max turns (10) exceeded -> JSON fallback timeout -> mock fallback` chain
- the `competition_recommendation` provider tool path was narrowed so the model now sees one compact local grounding tool instead of a multi-tool recommendation loop
- recommendation runs now use per-run unique SDK session ids, which prevents old SQLite session memory from contaminating repeated spot checks
- runtime reporting now distinguishes:
  - `structured_direct_success`
  - `json_fallback_success`
  - `mock_fallback_success`
- there is now a dedicated single-case Ark debug script for `recommendation-003` style failures:
  - `backend/scripts/debug_agents_sdk_case.py`
- CI now exposes a manual workflow path for single-case `agents_sdk` repro, in addition to the existing spot check job

Current interpretation:

- `completed` + `effective_runtime_mode=agents_sdk` + `provider_success_path=structured` means true Ark structured direct success
- `completed` + `effective_runtime_mode=agents_sdk` + `provider_success_path=plain_json_fallback` means Ark structured failed, but the provider-side JSON fallback still completed without mock
- `completed` + `used_mock_fallback=true` means provider failed and mock finished the run

Latest local Phase 5G spot check:

- `recommendation-003` now completes on the real `agents_sdk` structured path with strict mode and no mock fallback
- the latest `agents_sdk` 3x3 sample produced `direct_success_rate=1.000`, `structured_direct_success_rate=1.000`, `mock_fallback_success_rate=0.000`
- the public GitHub Actions API for `origin` currently reports `0 workflows / 0 workflow runs`, so the workflow is ready in-repo but remote execution evidence is still pending

## Phase 5F Update

### Phase 5F+hotfix note

This hotfix specifically targets `competition_recommendation` on the `agents_sdk` path.

What was fixed:

- recommendation output normalization now repairs known provider drift before strict Pydantic validation
- fuzzy `task_type` variants such as `algorithm_*_competition_recommendation` are normalized back to `competition_recommendation`
- recommendation items can recover `competition_name` / `competition_id` from provider-shaped fields such as `id`, `name`, or nested `competition`
- `risk_overview` objects are normalized into the canonical string list
- unsupported extra fields are stripped before final validation
- recommendation provider tool output is compacted to avoid `None`-shaped fields leaking into later function-call arguments

Current limitation:

- the recommendation chain is no longer primarily blocked by the previously known schema-drift fields
- the main blocker in the latest real `agents_sdk` spot check is provider availability: Ark returned `403 AccountOverdueError`, which forced mock fallback
- because of that, `completed` still must be interpreted together with `effective_runtime_mode` and `used_mock_fallback`

The repo is currently at Phase 5F. The focus of this stage is not adding new product features. The focus is clarifying runtime semantics, improving Ark direct-success behavior, and making regression checks easier to trust.

What changed in Phase 5F:

- `runtime_mode` now has two supported values only: `mock` and `agents_sdk`
- `live` is no longer accepted and now fails fast with a clear migration message
- every run exposes `requested_runtime_mode`, `effective_runtime_mode`, `effective_model`, `used_mock_fallback`, and `fallback_reason`
- `agents_sdk` evaluation is separated from mock evaluation
- the frontend status panel distinguishes `Ark direct success` from `mock fallback`
- the repo now includes a minimal GitHub Actions CI matrix for Windows and Ubuntu

Current interpretation rules:

- `completed` does not automatically mean the Ark provider succeeded directly
- `completed` + `used_mock_fallback=true` means the provider path failed and the run was completed by mock fallback
- `requested_runtime_mode=agents_sdk` + `effective_runtime_mode=agents_sdk` + `used_mock_fallback=false` is the direct-success case


CompAssistant 现在不再只是一个 `competitions` 列表项目，而是一个保留原有竞赛数据能力、同时补齐最小 Agent 演示闭环的仓库。

当前已经落到 Phase 5E，核心能力包括：

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
- `agents_sdk` 专用评测入口
- 最小浏览器级 Playwright smoke

`payload` 仍然是内部 canonical representation。Simple Mode 只是输入适配层，不改变现有 task API；Advanced Mode 继续保留给调试、演示和评测使用。

## Runtime Mode 语义

当前正式支持的 runtime mode 只有两个：

- `mock`
- `agents_sdk`

旧的 `live` 别名不再接受。若继续传入 `--runtime-mode live` 或对应配置，系统会直接报错并提示改用 `agents_sdk`。

运行结果的解释规则：

- `requested_runtime_mode`：请求方想跑的模式
- `effective_runtime_mode`：本次 run 最终实际产出的模式
- `effective_model`：最终实际使用的模型标识
- `used_mock_fallback`：真实 provider 失败后是否降级到了 mock
- `fallback_reason`：触发 mock fallback 的原因

这意味着：

- `mock` 成功不等于 `agents_sdk` 成功
- `completed` 不一定代表真实 Ark provider 直出成功
- 若 `used_mock_fallback=true`，则该 run 虽然可能 `completed`，但语义上是“provider 失败后经 mock 降级补全”

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
- `frontend/e2e/agent-control-errors.spec.ts`

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

真实 Ark 路径 spot check：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval_agents_sdk.py --sample-per-task-type 3
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
- 当前正式 runtime mode 只有 `mock / agents_sdk`
- `completed` 仍需结合 `effective_runtime_mode` 与 `used_mock_fallback` 一起解释
- attachments 仍只是元数据入口，不是完整多模态能力
- 浏览器级 smoke 目前覆盖 1 条 recommendation happy path 与 1 条 control failure detail
- `competitions` 页面与 API 保持兼容，未被本轮改动破坏
