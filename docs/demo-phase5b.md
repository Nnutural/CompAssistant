# Phase 5C-mini Demo

## 目标

演示以下能力已经形成最小闭环：

- Agent 面板已支持简洁模式 / 高级模式双输入
- 创建任务后立即返回 `run_id`
- 前端可继续轮询状态、事件、结果和历史任务
- Advanced Mode 仍可直接编辑 canonical payload
- retry / cancel / review 仍可正常使用

## 演示步骤

1. 启动后端与前端。
2. 打开 `智能体面板`。
3. 保持 `简洁模式`，选择 `竞赛推荐`。
4. 填写方向、年级、能力标签和偏好标签。
5. 确认页面已经显示“将要提交的 objective / payload 预览”。
6. 点击 `创建任务`，确认页面立即显示 `run_id`。
7. 观察状态从 `排队中` 推进到终态，并看到事件时间线。
8. 终态后查看 `结果产物` 和 `最近任务`。
9. 从当前任务切换到 `高级模式`，确认仍可直接编辑 JSON。
10. 任选一个终态任务，继续演示 `重试`、`取消` 或 `审核`（按状态可用）。
11. 如需核对后端实际收到的请求，取 `ledger_id` 后访问兼容 ledger 路由查看 `request_objective / request_payload`。

## 命令

后端：

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

前端：

```bash
cd frontend
npm run dev
```

评测：

```bash
backend\.venv\Scripts\python backend/scripts/run_eval.py --runtime-mode mock
```
