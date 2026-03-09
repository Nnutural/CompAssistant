# Agent 面板说明

当前目录承载 Phase 5B 的最小智能体面板：

- 创建任务
- 轮询状态
- 查看事件时间线
- 查看 artifacts
- 查看历史任务
- 执行 retry / cancel / review

关键文件：

- `AgentPanel.vue`
- `components/TaskForm.vue`
- `components/RunStatus.vue`
- `components/EventTimeline.vue`
- `components/ArtifactPanel.vue`
- `components/TaskHistoryList.vue`
- `config.ts`

约束：

- 所有任务 API 调用统一走 `frontend/src/api/agent.ts`
- 所有任务类型统一走 `frontend/src/types/agent.ts`
- 新 UI 不直接依赖 legacy `/api/research-runtime/*`
