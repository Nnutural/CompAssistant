# 后端智能体指南

作用范围：本指南适用于 `backend/`。

## 当前后端现实情况

- 当前激活的 FastAPI 入口是 `backend/app/main.py`。
- 路由目前组织在 `backend/app/api/routes/` 下。
- Pydantic 响应模型目前位于 `backend/app/schemas/` 下。
- 竞赛数据来自 `backend/data/competitions.json`。
- `backend/app/core/config.py` 定义了 MySQL 相关配置，但当前请求流程并未真正使用数据库层。

## 护栏规则

- 不要破坏 `app.main`、`app.api`、`app.schemas`、`app.core` 下的现有导入关系。
- 在用户明确要求接线之前，新建的后端目录都应保持解耦状态。
- 仅将 `backend/.env.example` 作为提交到仓库的环境变量模板。
- 在新增代码前，优先文档化仓储层、服务层、worker、工具和智能体的边界。

## 占位区域

- `backend/app/agents/`：未来用于编排层与智能体适配器。
- `backend/app/tools/`：未来用于可被智能体调用的工具封装。
- `backend/app/services/`：未来当项目超出直接路由逻辑时可承载业务服务。
- `backend/app/repositories/`：未来若 JSON 存储被替换，可承载持久化抽象层。
- `backend/app/workers/`：未来用于异步或定时执行模块。
- `backend/app/tests/`：未来用于后端测试与测试夹具。
