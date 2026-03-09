# 前端接入说明

## 推荐接入路径

前端应优先接入新的任务 API，而不是直接绑定旧的 `research-runtime` 路由：

1. `POST /api/agent/tasks`
2. 记录返回的 `run_id`
3. 轮询 `GET /api/agent/tasks/{run_id}`
4. 轮询 `GET /api/agent/tasks/{run_id}/events`
5. 在终态后读取 `GET /api/agent/tasks/{run_id}/artifacts`
6. 按需读取 `GET /api/agent/tasks` 展示历史任务
7. 按需调用 `retry / cancel / review` 控制接口

## Phase 5B 任务控制

当前已提供最小控制面：

- `POST /api/agent/tasks/{run_id}/retry`
- `POST /api/agent/tasks/{run_id}/cancel`
- `POST /api/agent/tasks/{run_id}/review`

控制接口约束：

- `retry` 适用于已结束任务，并会生成新的 run 记录
- `cancel` 适用于 `queued` / `running`
- `review` 适用于 `awaiting_review`

前端应把这些控制接口视为“显式操作”，不要在后台静默自动调用。

## 轮询模型

`POST /api/agent/tasks` 当前行为：

- 立即创建 ledger
- 写入 `received -> queued` 事件
- 返回 `201` 和 `run_id`
- 在进程内线程池中继续执行

典型状态推进：

- `queued`
- `running`
- `planning`
- `retrieving_local_context`
- `reasoning`
- `validating_output`
- `persisting_artifacts`
- `completed` / `failed` / `cancelled` / `awaiting_review`

## 前端目录

当前最小 Agent 面板位于：

- `frontend/src/features/agent/AgentPanel.vue`
- `frontend/src/features/agent/components/TaskForm.vue`
- `frontend/src/features/agent/components/RunStatus.vue`
- `frontend/src/features/agent/components/EventTimeline.vue`
- `frontend/src/features/agent/components/ArtifactPanel.vue`
- `frontend/src/features/agent/components/TaskHistoryList.vue`

共享契约：

- API client: `frontend/src/api/agent.ts`
- Types: `frontend/src/types/agent.ts`

不要把原始 Axios 请求散落到页面组件中。

## 轮询默认值

集中配置位于：

- `frontend/src/features/agent/config.ts`

当前默认：

- `AGENT_POLL_INTERVAL_MS = 1500`
- `AGENT_HISTORY_PAGE_SIZE = 8`

## 历史任务列表

`GET /api/agent/tasks` 当前支持：

- 按状态筛选
- 按任务类型筛选
- 倒序读取
- `limit / offset` 分页

返回摘要字段至少包括：

- `run_id`
- `task_type`
- `status`
- `current_state`
- `artifact_count`
- `has_artifacts`
- `awaiting_review`
- `available_actions`
- `created_at`
- `updated_at`

## 稳定响应约束

状态接口返回：

- `run_id`
- `status`
- `current_state`
- `completed_states`
- `error_stage`
- `result`
- `artifact_count`
- `available_actions`

事件接口返回：

- `event_id`
- `state`
- `status`
- `message`
- `actor`
- `detail`
- `created_at`

产物接口返回：

- `artifact_id`
- `artifact_type`
- `title`
- `payload`
- `ref`
- `created_at`

在任务未结束前，`artifacts.items` 允许为空，前端应把它当作正常状态。

## 当前限制

- 后台执行是进程内线程池，不跨进程持久恢复
- 暂无 WebSocket
- 暂无完整审批工作流
- 暂无任务批量管理或复杂查询
