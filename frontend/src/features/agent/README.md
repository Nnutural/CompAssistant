# Agent 面板说明

当前目录承载 Phase 5C-mini 的最小智能体面板：

- 创建任务
- 轮询状态
- 查看事件时间线
- 查看 artifacts
- 查看历史任务
- 执行 retry / cancel / review
- 使用简洁模式 / 高级模式双输入

关键文件：

- `AgentPanel.vue`
- `components/TaskForm.vue`
- `components/RunStatus.vue`
- `components/EventTimeline.vue`
- `components/ArtifactPanel.vue`
- `components/TaskHistoryList.vue`
- `config.ts`
- `input_adapter.ts`

约束：

- 所有任务 API 调用统一走 `frontend/src/api/agent.ts`
- 简洁模式只做输入适配，最终仍生成 canonical payload
- 高级模式继续保留给调试、演示和评测
- 附件当前只写入 `payload.attachments` 元数据，不上传、不由 runtime 消费
