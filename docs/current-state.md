# 当前状态

本文档基于 2026-03-10 的仓库状态更新。

## 已完成能力

后端：

- FastAPI 已提供 `competitions`、`research-runtime`、`agent/tasks` 三组路由
- 真实执行链路仍是 `FastAPI route -> ResearchRuntimeService -> mock manager / Ark-only Agents SDK runtime -> LedgerRepository`
- 三类主任务可运行：
  - `competition_recommendation`
  - `competition_eligibility_check`
  - `competition_timeline_plan`
- legacy `research_plan` 仍保兼容
- 已有显式状态机、events、artifacts、历史列表、`retry / cancel / review`
- 已有 output repair / validation 和本地领域数据 grounding

前端：

- 现有 `competitions` 页面保留
- 已有最小 Agent 面板
- 已支持状态轮询、事件时间线、artifacts、历史任务和控制入口
- 已支持 `简洁模式 / 高级模式` 双模式输入
- `eligibility / timeline` 的 Simple Mode 已补充竞赛建议列表，最终仍提交 canonical `competition_id`

评测与演示：

- `backend/data/evals/` 已有本地样例
- `backend/scripts/run_eval.py` 可运行结构 + 质量混合回归
- 前端已有最小 Playwright browser smoke
- 已补 demo fixtures、demo checklist 和演示文档

## 当前边界

- `payload` 仍然是内部 canonical representation
- Simple Mode 只是输入适配层，不改变 task API
- attachments 仍只写入 `payload.attachments` 元数据
- competitions API 继续保持可用

## 未完成能力

- 没有聊天式产品输入层
- 没有真正的多模态 runtime 消费链路
- 没有 WebSocket
- 没有 Redis / Celery / 消息队列
- 没有跨进程 durable 恢复
- 没有完整审批流或复杂权限体系

## 已知限制

- 背景执行仍基于进程内线程池
- `cancel` 是协作式取消，不是强制打断底层模型调用
- 浏览器级 smoke 当前只覆盖一条 recommendation happy path 和一次 retry 动作
- `review` 仍以最小 operator 动作为主，未纳入自动化 smoke
- 附件只是输入占位元数据，不代表已完成完整多模态推理
