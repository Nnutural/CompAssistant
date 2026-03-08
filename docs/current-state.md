# 当前状态快照

本快照基于 2026-03-08 的仓库状态编写。

## 后端

- 框架：FastAPI。
- 入口：`backend/app/main.py`。
- 路由聚合：`backend/app/api/api.py`。
- 当前激活路由：`backend/app/api/routes/competitions.py`。
- 当前激活 schema：`backend/app/schemas/competition.py`。
- 数据来源：`backend/data/competitions.json`。
- 当前行为：从 JSON 中读取竞赛数据，解析截止时间，排序后暴露列表与详情接口。
- 当前尚未实现：仓储层、服务层、后台 worker、测试体系或智能体运行时。

## 前端

- 框架：Vue 3 + Vite。
- 入口：`frontend/src/main.js`。
- 主壳层：`frontend/src/App.vue`。
- 现有视图/组件：`CompetitionList.vue` 与 `Guide.vue`。
- 当前行为：展示竞赛列表，请求 `/api/competitions`，在前端做筛选，并以弹窗形式展示详情。
- 当前尚未实现：独立 API 客户端层、共享类型层或面向智能体的前端功能。

## 配置现状

- `backend/app/core/config.py` 定义了应用元信息和 MySQL 相关配置。
- 当前后端请求流程尚未真正实例化或使用数据库连接。
- 当前前端已经有自己的 `.gitignore` 与包管理清单。

## 对未来智能体工作的含义

- 后续智能体集成应先从契约、文档和占位结构开始。
- 运行时接线应被视为后续阶段工作。
- 在未收到明确迁移请求前，当前基于 JSON 的竞赛行为应保持为默认基线。
