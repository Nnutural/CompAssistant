# 文档总览

当前文档已经从早期脚手架说明扩展到可运行 runtime、前端接入、评测与数据治理说明。

## 建议优先阅读

- `current-state.md`：当前仓库真实状态快照
- `agent-runtime-overview.md`：后端运行时、路由、service、ledger 关系
- `data-inventory.md`：当前项目数据对象总台账
- `data-sources.md`：当前项目数据来源与接入状态
- `data-contracts.md`：核心 task / status / event / artifact / adapter 契约
- `data-engineering-rules.md`：数据工程规则与维护约束
- `data-manifest.json`：最小机器可读数据清单
- `task-types.md`：3 类主任务输入输出说明
- `ledger-state-machine.md`：显式状态机、events、artifacts 说明
- `frontend-integration.md`：前端应如何接入新的 task API
- `evaluation.md`：本地 eval dataset 与回归脚本说明
- `schemas/`：核心 JSON Schema

## 仍保留的脚手架文档

- `codex-agent-scaffold.md`
- `repository-hygiene.md`
- `ai-crawler-placeholder.md`

## 文档策略

- 文档必须与当前实现一致。
- 新增数据对象、数据来源、契约或持久化边界时，优先同步 `data-*` 系列文档。
- 前端新接入优先参考 `/api/agent/tasks/*`。
- legacy `research-runtime` 路由只作为兼容入口保留。
