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
3. 保留默认模板，点击 `创建任务`。
4. 观察页面立刻显示 `run_id` 与 `排队中`。
5. 等待状态推进到终态。
6. 查看时间线、artifacts 与历史任务列表。

## 查看任务状态

推荐入口：

- `GET /api/agent/tasks/{run_id}`
- `GET /api/agent/tasks/{run_id}/events`
- `GET /api/agent/tasks/{run_id}/artifacts`

如果需要查看历史：

- `GET /api/agent/tasks?status=awaiting_review`
- `GET /api/agent/tasks?task_type=competition_recommendation`
- `GET /api/agent/tasks?limit=10&offset=0`

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
- 新 run 与原 run 的关系会写入 ledger / events / control_records

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
- `annotate`：任务保持 `awaiting_review`，但写入审核备注和事件

## 评测

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock
```

如果需要看完整报告：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock --json
```
