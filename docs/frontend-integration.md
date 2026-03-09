# Frontend Integration

## 推荐接入方式

前端新接入应优先使用新的 task API，不要直接依赖旧 `research-runtime` 路由。

推荐调用顺序：

1. `POST /api/agent/tasks`
2. 读取返回的 `run_id`
3. 轮询 `GET /api/agent/tasks/{run_id}`
4. 按需读取 `GET /api/agent/tasks/{run_id}/events`
5. 按需读取 `GET /api/agent/tasks/{run_id}/artifacts`

## 前端已准备的文件

- `frontend/src/api/agent.ts`
- `frontend/src/types/agent.ts`
- `frontend/src/features/agent/README.md`

## `agent.ts` 提供的调用

- `createAgentTask`
- `getAgentTaskStatus`
- `getAgentTaskEvents`
- `getAgentTaskArtifacts`
- `agentTaskApi`

## 轮询建议

- 提交任务后立即保存 `run_id`
- 每隔 1 到 2 秒轮询一次 status
- 当 `status` 进入以下之一时停止高频轮询：
  - `completed`
  - `failed`
  - `awaiting_review`
- `events` 可较低频拉取
- `artifacts` 建议在任务进入终态后读取

## 契约对齐原则

- TypeScript types 与后端 DTO 对齐
- `run_id` 是轮询主键
- `task_id` 保持与 legacy envelope 的兼容映射
- `events` 和 `artifacts` 都是稳定结构，不依赖组件自行猜字段
