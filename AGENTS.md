# 仓库级智能体指南

作用范围：本指南适用于整个仓库。

## 当前基线

- 后端是一个位于 `backend/app` 下的小型 FastAPI 服务。
- 前端是一个位于 `frontend/src` 下的 Vue 3 + Vite 应用。
- 当前业务行为由 `backend/data/competitions.json` 和现有 UI 组件驱动。
- 当前仓库中尚未实现多智能体运行时。

## 工作规则

- 保持现有 `backend/` 和 `frontend/` 结构不变。
- 优先新增内容，而不是修改现有运行时代码。
- 将 `.codex/`、`docs/`、`backend/app/agents/`、`backend/app/tools/`、`backend/app/services/`、`backend/app/repositories/`、`backend/app/workers/`、`backend/app/tests/`、`frontend/src/api/`、`frontend/src/features/agent/`、`frontend/src/types/` 视为支撑性脚手架区域。
- 除非用户明确要求实现，否则不要从这些占位区域接入导入关系、路由、后台任务、SDK 客户端或 UI 流程。
- 在规划更大范围改动前，先阅读 `docs/current-state.md` 和 `docs/codex-agent-scaffold.md`。
- 在判断哪些内容应提交到版本库时，参考 `GIT_TRACKING.md` 和 `docs/repository-hygiene.md`。

## 后续 Codex 工作的默认预期

- 当请求涉及智能体相关工作时，先文档化意图，再进入实现。
- 让 schema 和文档先于运行时集成落地。
- 真实凭证、密钥和外部 API 调用应留到后续明确实现阶段。
