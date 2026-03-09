# Agent Runtime Overview

## 目标

当前 runtime 已经从早期 research demo 收敛为适配竞赛助手产品的后端运行核心，并在 Phase 4B 上增加了可轮询、可评测、可前端接入的契约层。

## 主链路

```text
POST /api/agent/tasks
  -> ResearchRuntimeService.create_agent_task()
  -> ResearchRuntimeService.run_task()
  -> mock manager 或 Ark-only Agents SDK runtime
  -> LedgerRepository
  -> GET /api/agent/tasks/{run_id} /events /artifacts
```

## 运行模式

- `mock`
  - 本地稳定回归基线
  - 三类主任务均已支持
- `agents_sdk`
  - 真实 Ark-only + `chat_completions` 模式
  - 仍保留 mock fallback

## 核心组件

- `backend/app/api/routes/agent_tasks.py`
  - 面向前端轮询的统一 task API
- `backend/app/api/routes/research_runtime.py`
  - legacy 兼容入口
- `backend/app/services/research_runtime_service.py`
  - 总控层，负责建 task、运行 runtime、读取 ledger
- `backend/app/repositories/ledger_repository.py`
  - 以 JSON 文件持久化 ledger
- `backend/app/agents/`
  - manager、orchestrator、specialists、output repair / validation
- `backend/app/tools/competition_runtime.py`
  - 本地领域数据读取与 grounding 工具

## Phase 4B 新增内容

- 新统一任务 API
- 薄 DTO：status / events / artifacts
- 本地 eval dataset 与回归脚本
- 前端 API client / types 占位

## 当前边界

- 不使用 WebSocket
- 不引入后台队列或 worker
- `POST /api/agent/tasks` 当前仍为同步提交并立即执行
- 前端需要通过 `run_id` 读取后续状态、events 和 artifacts
