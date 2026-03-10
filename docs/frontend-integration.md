# 前端接入说明

## 推荐接入路径

前端应优先接入新的任务 API，而不是直接绑定旧的 `research-runtime` 路由：

1. `POST /api/agent/tasks`
2. 记录返回的 `run_id`
3. 轮询 `GET /api/agent/tasks/{run_id}`
4. 轮询 `GET /api/agent/tasks/{run_id}/events`
5. 终态后读取 `GET /api/agent/tasks/{run_id}/artifacts`
6. 按需读取 `GET /api/agent/tasks` 展示历史任务
7. 按需调用 `retry / cancel / review` 控制接口

## 运行语义展示

前端状态区建议同时展示以下字段：

- `requested_runtime_mode`
- `effective_runtime_mode`
- `effective_model`
- `used_mock_fallback`
- `fallback_reason`

原因：

- `completed` 不一定等于真实 provider 直出成功
- 如果 `requested_runtime_mode="agents_sdk"` 但 `effective_runtime_mode="mock"`，说明本次 run 经历了 mock fallback
- 前端不应把“任务完成”直接翻译成“Ark 成功”

## Phase 5C-mini 输入层

当前 Agent 面板位于：

- `frontend/src/features/agent/AgentPanel.vue`
- `frontend/src/features/agent/components/TaskForm.vue`
- `frontend/src/features/agent/components/RunStatus.vue`
- `frontend/src/features/agent/components/EventTimeline.vue`
- `frontend/src/features/agent/components/ArtifactPanel.vue`
- `frontend/src/features/agent/components/TaskHistoryList.vue`

共享契约：

- API client：`frontend/src/api/agent.ts`
- Types：`frontend/src/types/agent.ts`

当前输入层采用双模式：

- `简洁模式`
  - 只暴露最小产品表单
  - 根据 task_type 自动组装 `objective + payload`
  - 提交前展示 payload 预览
  - `eligibility / timeline` 会给出竞赛建议列表，但最终仍提交 canonical `competition_id`
- `高级模式`
  - 保留原始 `objective + payload JSON` 编辑器
  - 适合调试、评测和精确构造 case

## Phase 5D-lite 补充

- 当前仓库已补最小浏览器级 smoke：
  - `frontend/playwright.config.ts`
  - `frontend/e2e/agent-panel.spec.ts`
  - `frontend/e2e/agent-control-errors.spec.ts`
  - `frontend/e2e/fixtures/agent-demo-cases.json`
- 这套 smoke 不改变前后端契约，只验证现有面板和 API 的 happy path。

## payload 不变原则

- `payload` 仍然是内部 canonical representation
- `Simple Mode` 只是输入适配层，不改变 task API 形状
- 后端 runtime 继续消费现有 canonical payload

当前映射规则：

- `competition_recommendation`
  - `direction -> payload.profile.direction`
  - `grade -> payload.profile.grade`
  - `abilities -> payload.profile.ability_tags`
  - `preference_tags -> payload.profile.preference_tags`
  - `extra_notes -> payload.profile.extra_notes`
- `competition_eligibility_check`
  - 竞赛选择最终写入 `payload.competition_id`
  - `grade -> payload.profile.grade`
  - `achievements / prerequisites` 一方面派生到 `payload.profile.ability_tags`，另一方面保留原始文本字段
  - `team_mode -> payload.profile.preference_tags`
  - `extra_notes -> payload.profile.extra_notes`
- `competition_timeline_plan`
  - 竞赛选择最终写入 `payload.competition_id`
  - `deadline -> payload.deadline`
  - `weekly_hours -> payload.constraints.available_hours_per_week`
  - `current_stage / goals / constraints / extra_notes -> payload.constraints.notes`

## 竞赛选择策略

- `eligibility` 与 `timeline` 的 Simple Mode 会读取 `/api/competitions`
- 界面展示竞赛名称搜索/选择
- 提交时仍只写 canonical `competition_id`
- 如果竞赛列表加载失败，界面退化为手动输入 `competition_id`

## 附件预留位

当前仅预留附件元数据入口：

```json
{
  "attachments": [
    {
      "name": "resume.pdf",
      "kind": "document",
      "mime_type": "application/pdf",
      "local_ref": "local-file://resume.pdf-1234-1700000000"
    }
  ]
}
```

约束：

- 当前不上传文件
- 当前 runtime 不消费这些附件
- 这里只是为未来多模态输入预留可选元数据位

## 轮询默认值

集中配置位于：

- `frontend/src/features/agent/config.ts`

当前默认值：

- `AGENT_POLL_INTERVAL_MS = 1500`
- `AGENT_HISTORY_PAGE_SIZE = 8`

## 当前限制

- 后台执行仍是进程内线程池，不跨进程恢复
- 暂无 WebSocket
- 暂无完整审批流
- 附件只是元数据入口，不代表完整多模态能力
