# Ledger State Machine

## 状态定义

当前 runtime 显式记录以下状态：

1. `received`
2. `planning`
3. `retrieving_local_context`
4. `reasoning`
5. `validating_output`
6. `persisting_artifacts`
7. `completed`
8. `failed`
9. `awaiting_review`

## 记录方式

状态与事件都写入 `ResearchLedger`：

- `current_state`
- `completed_states`
- `error_stage`
- `events`
- `raw_outputs`
- `repaired_outputs`
- `validation_errors`
- `parse_errors`
- `artifacts`

## events 结构

每个 event 至少包含：

- `event_id`
- `state`
- `status`
- `message`
- `actor`
- `detail`
- `created_at`

这些字段足以支撑前端 timeline 展示。

## artifacts 结构

每个 runtime artifact 至少包含：

- `artifact_id`
- `artifact_type`
- `title`
- `payload`
- `created_at`

这些字段足以支撑前端结果卡片展示。

## 失败与审核

- 若运行失败：
  - `current_state = failed`
  - `error_stage` 会记录失败发生阶段
  - `blockers`、`validation_errors`、`parse_errors` 会保留可解释信息
- 若结果可修复但仍需人工确认：
  - `current_state = awaiting_review`
  - `result_status = needs_human`

## 前端建议

- 状态轮询以 `run_id` 为主键
- timeline 使用 `/api/agent/tasks/{run_id}/events`
- 结果卡片使用 `/api/agent/tasks/{run_id}/artifacts`
- 摘要区使用 `/api/agent/tasks/{run_id}`
