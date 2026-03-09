# Agent Feature Stub

此目录为后续最小 Agent 面板预留。

当前 Phase 4B 只完成契约层准备，不改造现有页面：

- API 调用统一放在 `frontend/src/api/agent.ts`
- 共享类型统一放在 `frontend/src/types/agent.ts`
- 前端轮询主键使用 `run_id`
- 新页面应优先调用 `/api/agent/tasks/*`，不要直接依赖旧 `/api/research-runtime/*` 路由

建议后续最小接入流程：

1. 调用 `createAgentTask` 创建任务并拿到 `run_id`
2. 轮询 `getAgentTaskStatus`
3. 按需读取 `getAgentTaskEvents` 渲染 timeline
4. 读取 `getAgentTaskArtifacts` 渲染结果卡片
