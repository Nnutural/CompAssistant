# 前端智能体指南

作用范围：本指南适用于 `frontend/`。

## 当前前端现实情况

- 当前应用使用 Vue 3 + Vite。
- 当前入口文件是 `frontend/src/main.js`。
- 现有 UI 逻辑主要集中在 `frontend/src/App.vue` 与 `frontend/src/components/`。
- API 请求目前由 `CompetitionList.vue` 组件直接通过 `axios` 发起。

## 护栏规则

- 除非用户明确要求，否则不要重命名或移动现有组件结构。
- 在真正实现前，新增的前端占位内容应与当前 UI 保持隔离。
- 任何环境变量约定都以 `frontend/.env.example` 为说明模板。
- 在引入运行时使用前，优先文档化 API 客户端、智能体功能边界和共享类型。

## 占位区域

- `frontend/src/api/`：未来用于薄封装的请求层与传输辅助逻辑。
- `frontend/src/features/agent/`：未来用于智能体相关 UI 面板、状态与组合逻辑。
- `frontend/src/types/`：未来用于共享前端类型或 JSDoc 类型锚点。
