# Schema 契约说明

这些 schema 用于描述未来 Codex 任务或多智能体交接时可能交换的结构化文档。

## 范围

- 仅定义数据结构形状。
- 保持与具体实现解耦。
- 支持文档说明、校验和后续 API 规划。

## 当前文件

- `agent-task-envelope.schema.json`：入站任务/请求的契约。
- `agent-handoff.schema.json`：agent 间委派与交接的契约。
- `agent-result.schema.json`：已完成或受阻任务的标准结果契约。
