# Operator Guide

## 启动后端

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 启动前端

```bash
cd frontend
npm run dev
```

## 跑一个最小 demo

1. 打开前端页面。
2. 点击侧栏 `智能体面板`。
3. 保持 `简洁模式`，选择一个任务类型。
4. 填写自然表单，确认页面中已展示“将要提交的 objective / payload 预览”。
5. 点击 `创建任务`。
6. 确认页面立即显示 `run_id` 和 `排队中`。
7. 继续观察状态、事件时间线、结果产物和历史任务列表。

## 使用简洁模式

适用场景：

- 面向普通演示
- 不希望直接暴露 payload schema
- 需要快速生成合规输入

行为说明：

- 简洁模式只负责输入适配
- 最终仍然会生成 `objective + payload`
- 生成结果会在提交前显示预览
- 竞赛选择会优先按名称搜索，但最终仍提交 canonical `competition_id`

## 使用高级模式

适用场景：

- 调试
- 回归测试
- 精确构造 case

行为说明：

- 保留原始 `objective + payload JSON` 编辑体验
- payload 仍是内部 canonical representation
- 从简洁模式切换到高级模式时，会把当前简洁表单生成的请求同步到编辑器
- 高级模式中的自定义 JSON 会被本地保留，并可恢复上次草稿

## 查看任务状态

推荐入口：

- `GET /api/agent/tasks/{run_id}`
- `GET /api/agent/tasks/{run_id}/events`
- `GET /api/agent/tasks/{run_id}/artifacts`

如果需要查看历史：

- `GET /api/agent/tasks?status=awaiting_review`
- `GET /api/agent/tasks?task_type=competition_recommendation`
- `GET /api/agent/tasks?limit=10&offset=0`

如需核对后端实际收到的请求：

- 先读取 `GET /api/agent/tasks/{run_id}` 拿到 `ledger_id`
- 再读 `GET /api/research-runtime/ledger/{ledger_id}`
- 核对其中的 `request_objective` 和 `request_payload`

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

接口：

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

## 评测

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock
```

完整 JSON 报告：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock --json
```
