# Codex 与智能体脚手架说明

当前仓库已经加入一批占位位置，用于承接未来 Codex 辅助工作和多智能体相关扩展。

## 为什么这些目录存在

- 为未来工作提供稳定的落点。
- 将文档与契约同运行时代码分离。
- 避免过早接入到当前 FastAPI 与 Vue 的真实流程中。

## 后端占位区域

- `backend/app/agents/`：未来用于编排入口和智能体适配模块。
- `backend/app/tools/`：未来用于供智能体调用的工具适配层。
- `backend/app/services/`：未来若抽离路由逻辑，可承载业务服务层。
- `backend/app/repositories/`：未来若存储超出当前 JSON 文件，可承载持久化适配层。
- `backend/app/workers/`：未来用于异步或定时执行逻辑。
- `backend/app/tests/`：未来用于后端测试。

## 前端占位区域

- `frontend/src/api/`：未来用于代替组件内直连请求的请求封装层。
- `frontend/src/features/agent/`：未来用于智能体任务、状态或历史记录相关 UI。
- `frontend/src/types/`：未来用于共享 API 与 UI 类型定义。

## Codex 支撑区域

- `.codex/config.toml`：仓库本地 Codex 配置样例。
- `.codex/actions/`：未来可复用的 Codex 操作说明。
- `.codex/setup/`：未来本地工作流准备说明。
- `.codex/skills/`：本仓库可复用的小型技能定义。
- `docs/schemas/`：未来交接与结构化输出所需契约。

## 当前明确不包含的内容

- 真实 OpenAI 或 Agents SDK 接线。
- 会实际执行在线任务的后台 worker。
- 面向智能体的 API 路由。
- 已连接真实智能体后端的前端 UI。
