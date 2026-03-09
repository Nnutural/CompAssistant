# 文档总览

当前文档已经从早期脚手架阶段推进到可运行 runtime 的说明阶段。

## 建议优先阅读

- `current-state.md`：当前仓库真实状态快照
- `agent-runtime-overview.md`：后端运行时、路由、service、ledger 关系
- `task-types.md`：3 类主任务输入输出说明
- `ledger-state-machine.md`：显式状态机、events、artifacts 说明
- `frontend-integration.md`：前端应如何接入新的 task API
- `evaluation.md`：本地 eval dataset 与回归脚本说明
- `schemas/`：核心契约 JSON Schema

## 仍保留的脚手架文档

- `codex-agent-scaffold.md`
- `repository-hygiene.md`

## 文档策略

- 文档必须与当前实现一致
- 前端新接入优先参考 `/api/agent/tasks/*`
- legacy `research-runtime` 路由只作为兼容入口保留
