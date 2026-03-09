# Phase 5B Demo

## 目标

演示以下能力已经形成闭环：

- 任务创建后立即返回
- 前端轮询任务状态与事件
- 历史任务可筛选与查看
- retry / cancel / review 可用
- 评测输出带基础质量区分

## 演示步骤

1. 启动后端与前端。
2. 打开 `智能体面板`。
3. 提交一个推荐任务，确认页面立刻显示 `run_id`。
4. 观察状态从 `排队中` 推进到终态。
5. 在 `最近任务` 区域确认能看到刚完成的记录。
6. 提交一个资格判断任务，等待进入 `待审核`。
7. 在当前任务卡片点击 `添加备注`，确认时间线出现 review note。
8. 点击 `审核通过` 或 `审核驳回`，确认状态变更。
9. 选择一个终态任务，点击 `重试`，确认生成新 run。
10. 提交一个慢任务并点击 `取消任务`，确认状态转为 `已取消`。
11. 运行本地 eval，确认输出含 `avg_quality` 和 `failed_checks`。

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
