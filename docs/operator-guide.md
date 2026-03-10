# Operator Guide

## 启动后端

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

如需更稳定的演示，建议显式使用 mock runtime：

```bash
set RESEARCH_RUNTIME_MODE=mock
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

如需验证真实 Ark 路径，请显式使用：

```bash
set RESEARCH_RUNTIME_MODE=agents_sdk
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

不要再使用 `RESEARCH_RUNTIME_MODE=live`。该别名已废弃并会直接报错。

## 启动前端

```bash
cd frontend
npm install
npm run dev
```

## 跑最小浏览器 smoke

首次安装浏览器：

```bash
cd frontend
npm run test:e2e:install
```

运行 smoke：

```bash
cd frontend
npm run test:e2e
```

当前 smoke 使用 mock runtime，覆盖：

- 打开 Agent 面板
- Simple Mode 填 recommendation case
- 查看 payload 预览
- 切换到 Advanced Mode
- 提交任务
- 查看状态、事件、artifacts、历史
- 执行一次 retry
- 验证一次 review 失败 detail 的页面展示
- 回到 competitions 页面

## 跑一个最小 demo

1. 打开前端页面。
2. 点击侧栏 `智能体面板`。
3. 保持 `简洁模式`，选择一个任务类型。
4. 填写自然表单。
5. 在提交前确认页面已经显示“将要提交的 objective / payload 预览”。
6. 点击 `创建任务`。
7. 确认页面立即显示 `run_id` 和 `排队中`。
8. 继续观察状态、事件时间线、结果产物和最近任务列表。

## 如何解释运行结果

推荐先看 `GET /api/agent/tasks/{run_id}` 中的以下字段：

- `requested_runtime_mode`
- `effective_runtime_mode`
- `effective_model`
- `used_mock_fallback`
- `fallback_reason`

解释规则：

- `requested_runtime_mode=mock`：本次本来就只跑 mock
- `requested_runtime_mode=agents_sdk` 且 `effective_runtime_mode=agents_sdk`：本次最终由 Ark 路径产出
- `requested_runtime_mode=agents_sdk` 且 `effective_runtime_mode=mock`：本次 Ark 路径失败后降级到了 mock
- `completed` 不能单独解释为“Ark 真实成功”，必须结合上面几个字段一起看

## Simple Mode

适用场景：

- 面向普通演示
- 不希望直接暴露 payload schema
- 需要快速得到符合 contract 的输入

行为说明：

- Simple Mode 只负责输入适配
- 最终仍然会生成 `objective + payload`
- 提交前会展示预览
- `eligibility / timeline` 的竞赛搜索会优先给出建议列表
- 页面始终显示最终将提交的 `competition_id`

## Advanced Mode

适用场景：

- 调试
- 回归测试
- 精确构造 case

行为说明：

- 保留原始 `objective + payload JSON` 编辑体验
- payload 仍然是内部 canonical representation
- 从简洁模式切换到高级模式时，会同步当前表单生成结果
- 高级模式中的自定义 JSON 会保留，且可恢复上次草稿

## 使用固定 demo fixtures

固定样例位于：

- `frontend/e2e/fixtures/agent-demo-cases.json`

当前建议演示的 3 条 case：

- `recommendation-001`
- `eligibility-009`
- `timeline-001`

若要专门验证真实 Ark 路径，请优先使用较小样本集，并观察是否出现 fallback：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval_agents_sdk.py --sample-per-task-type 3
```

每条 case 都包含：

- `task_type`
- `mode`
- `input`
- `expected_status`
- `expected_observations`

## 查看任务状态

推荐入口：

- `GET /api/agent/tasks/{run_id}`
- `GET /api/agent/tasks/{run_id}/events`
- `GET /api/agent/tasks/{run_id}/artifacts`

查看历史：

- `GET /api/agent/tasks?status=awaiting_review`
- `GET /api/agent/tasks?task_type=competition_recommendation`
- `GET /api/agent/tasks?limit=10&offset=0`

如需核对后端实际收到的请求：

1. 先读 `GET /api/agent/tasks/{run_id}` 拿到 `ledger_id`
2. 再读 `GET /api/research-runtime/ledger/{ledger_id}`
3. 核对其中的 `request_objective` 和 `request_payload`

## Retry

适用状态：

- `completed`
- `failed`
- `cancelled`
- `awaiting_review`

接口：

```bash
curl -X POST http://127.0.0.1:8000/api/agent/tasks/{run_id}/retry
```

效果：

- 创建新的 run
- 新 run 立即进入 `queued`
- 与原 run 的关系会写入 ledger / events / control_records

## Cancel

适用状态：

- `queued`
- `running`

接口：

```bash
curl -X POST http://127.0.0.1:8000/api/agent/tasks/{run_id}/cancel ^
  -H "Content-Type: application/json" ^
  -d "{\"note\":\"操作员取消任务\"}"
```

效果：

- 任务状态变为 `cancelled`
- 轮询接口会返回取消后的终态
- ledger / events 会记录取消动作

## Review

适用状态：

- `awaiting_review`

通过：

```bash
curl -X POST http://127.0.0.1:8000/api/agent/tasks/{run_id}/review ^
  -H "Content-Type: application/json" ^
  -d "{\"decision\":\"accept\",\"note\":\"人工审核通过\"}"
```

驳回：

```bash
curl -X POST http://127.0.0.1:8000/api/agent/tasks/{run_id}/review ^
  -H "Content-Type: application/json" ^
  -d "{\"decision\":\"reject\",\"note\":\"人工审核驳回\"}"
```

备注：

```bash
curl -X POST http://127.0.0.1:8000/api/agent/tasks/{run_id}/review ^
  -H "Content-Type: application/json" ^
  -d "{\"decision\":\"annotate\",\"note\":\"请导师进一步确认\"}"
```

效果：

- `accept`：任务转为 `completed`
- `reject`：任务转为 `failed`
- `annotate`：任务保持 `awaiting_review`，但会写入审核备注和事件

## 当前已知边界

- `cancel` 仍是协作式取消，不是强制终止 provider 调用
- `attachments` 只会记录到 `payload.attachments`，不会被 runtime 消费
- `queued / running` 任务不支持跨进程恢复
