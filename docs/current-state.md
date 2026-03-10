# 当前状态快照

本文档基于 2026-03-09 的仓库状态编写。

## 已完成能力

后端：

- FastAPI 已提供 `competitions`、`research-runtime`、`agent/tasks` 三组路由
- 真实执行链路为 `FastAPI route -> ResearchRuntimeService -> mock manager / Ark-only Agents SDK runtime -> LedgerRepository`
- 三类主任务已可运行：
  - `competition_recommendation`
  - `competition_eligibility_check`
  - `competition_timeline_plan`
- legacy `research_plan` 仍保兼容
- 已有显式状态机、events、artifacts、历史列表、retry / cancel / review
- 已有 output repair / validation 和本地领域数据 grounding

前端：

- 现有 competitions 页面仍保留
- 已有最小 Agent 面板
- 已支持状态轮询、事件时间线、artifacts、历史任务和控制入口
- Phase 5C-mini 已把输入层补成 `简洁模式 / 高级模式` 双模式

评测：

- `backend/data/evals/` 已有本地数据集
- `backend/scripts/run_eval.py` 可运行结构 + 质量混合回归

## 当前输入层

- `payload` 仍然是内部 canonical representation
- `简洁模式` 只做输入适配，不改变 task API
- `高级模式` 继续保留给调试、演示和评测
- 附件当前只写入 `payload.attachments` 元数据，不代表 runtime 已消费

## 当前 API

竞赛 API：

- `GET /api/competitions`
- `GET /api/competitions/{id}`

任务 API：

- `POST /api/agent/tasks`
- `GET /api/agent/tasks`
- `GET /api/agent/tasks/{run_id}`
- `GET /api/agent/tasks/{run_id}/events`
- `GET /api/agent/tasks/{run_id}/artifacts`
- `POST /api/agent/tasks/{run_id}/retry`
- `POST /api/agent/tasks/{run_id}/cancel`
- `POST /api/agent/tasks/{run_id}/review`

兼容 API：

- `POST /api/research-runtime/run`
- `GET /api/research-runtime/ledger/{ledger_id}`

## 未完成能力

- 没有完整聊天式输入层
- 没有真正的多模态 runtime 消费
- 没有 WebSocket
- 没有 Redis / Celery / 消息队列
- 没有真正 durable 的跨进程恢复
- 没有完整的审批工作流

## 已知限制

- 背景执行仍基于进程内线程池
- 取消是协作式取消，不是强制中断底层模型调用
- 附件只是元数据预留位
- 现有质量评测仍以本地规则和启发式 rubric 为主
