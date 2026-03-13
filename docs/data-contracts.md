# 数据契约

本页只整理当前仓库里最重要、最稳定、最需要维护同步的契约。

契约基线：

- 后端 API / runtime 主要以 `backend/app/schemas/agent_tasks.py` 与 `backend/app/schemas/research_runtime.py` 的 Pydantic 模型为准。
- 这些模型大多继承带 `ConfigDict(extra="forbid")` 的基类，所以默认 **不允许 additional properties**。
- 这些模型没有全局 `strict=True`，因此属于“**禁止额外字段，但仍允许 Pydantic 常规类型转换**”。
- 前端 `frontend/src/types/agent.ts` 是镜像类型，不是最终 source-of-truth。
- `docs/schemas/*` 与 `docs/examples/*` 当前主要覆盖 legacy runtime contract；新的 task API DTO 还没有单独 JSON Schema 文件。

## 关键枚举

| 枚举 | Canonical 值 |
| --- | --- |
| `TaskType` | `competition_recommendation`, `competition_eligibility_check`, `competition_timeline_plan`, `research_plan`, `source_discovery`, `evidence_extraction`, `synthesis`, `review`, `report_draft`, `schema_validation`, `general` |
| `TaskRunStatus` | `queued`, `running`, `completed`, `cancelled`, `failed`, `awaiting_review` |
| `RunState` | `received`, `queued`, `running`, `planning`, `retrieving_local_context`, `reasoning`, `validating_output`, `persisting_artifacts`, `completed`, `cancelled`, `failed`, `awaiting_review` |
| `RunEventStatus` | `entered`, `completed`, `error`, `warning`, `fallback`, `info` |
| `RuntimeMode` | `mock`, `agents_sdk` |
| `ControlAction` | `retry`, `cancel`, `review_accept`, `review_reject`, `review_annotate` |
| `ReviewDecision` | `accept`, `reject`, `annotate` |
| `provider_success_path` | `structured`, `plain_json_fallback` |

## 1. Task Create Request

契约名：`AgentTaskCreateRequest`

- 定义位置：`backend/app/schemas/agent_tasks.py`
- 前端镜像：`frontend/src/types/agent.ts`
- strict：否
- additional properties：否
- normalization / adapter：有。Simple Mode 会先经过 `frontend/src/features/agent/input_adapter.ts` 组装 canonical payload；service 会补默认 `objective`、`run_id`、`session_id`。

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `task_type` | `TaskType` | 是 | 当前前端 Simple Mode 只正式暴露 3 个 competition task type |
| `objective` | `string \| null` | 否 | 为空时由 service 按 `task_type` 补默认值 |
| `payload` | `object` | 是 | canonical 请求负载；后端不要求固定 shape |
| `task_id` | `string \| null` | 否 | 不传时 service 自动生成 `run-<id>` |
| `session_id` | `string \| null` | 否 | 不传时默认等于 `run_id` |
| `requested_by` | `user \| codex \| system \| agent` | 否 | 默认 `user` |
| `priority` | `low \| normal \| high` | 否 | 默认 `normal` |
| `constraints` | `string[]` | 否 | 默认空数组 |
| `dry_run` | `boolean` | 否 | 默认 `false` |

不允许静默修正：

- `task_type`
- `requested_by`
- `priority`
- `constraints` 的整体语义

当前允许的默认补全：

- `objective`
- `task_id`
- `session_id`

## 2. Task Status Response

契约名：`AgentTaskStatusResponse`

- 定义位置：`backend/app/schemas/agent_tasks.py`
- 生成位置：`ResearchRuntimeService._build_task_status_response()`
- strict：否
- additional properties：否
- normalization / adapter：有。该响应是从 `ResearchLedger` 派生，不是直接持久化对象。

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `run_id` | `string` | 是 | 当前 run 的主键 |
| `task_id` | `string` | 是 | 当前实现里与 `run_id` 一致 |
| `session_id` | `string` | 是 | 逻辑会话标识 |
| `ledger_id` | `string` | 是 | ledger 文件主键 |
| `task_type` | `TaskType \| null` | 否 | 由 ledger 派生 |
| `status` | `TaskRunStatus` | 是 | 由 `current_state` 映射得出 |
| `current_state` | `RunState \| null` | 否 | 当前状态机节点 |
| `completed_states` | `RunState[]` | 是 | 已完成状态节点 |
| `error_stage` | `RunState \| null` | 否 | 失败时记录 |
| `result` | `AgentTaskResultSummary` | 是 | `status` / `summary` / `finding_count` / `follow_up_items` / `blockers` |
| `requested_runtime_mode` | `string \| null` | 否 | 请求方想跑的模式 |
| `effective_runtime_mode` | `RuntimeMode \| null` | 否 | 最终实际产出的模式 |
| `effective_model` | `string \| null` | 否 | 最终实际使用模型或 `mock` |
| `provider_success_path` | `'structured' \| 'plain_json_fallback' \| null` | 否 | 仅 `agents_sdk` 且未 mock fallback 时才有意义 |
| `used_mock_fallback` | `boolean` | 是 | 是否降级到 mock |
| `fallback_reason` | `string \| null` | 否 | fallback 原因 |
| `elapsed_ms` | `number \| null` | 否 | 运行时长 |
| `event_count` | `number` | 是 | 来自 ledger.events |
| `artifact_count` | `number` | 是 | 终态时才统计 runtime artifact / final artifact |
| `available_actions` | `ControlAction[]` | 是 | 由当前状态推导 |
| `created_at` | `datetime` | 是 | ledger 创建时间 |
| `updated_at` | `datetime \| null` | 否 | ledger 更新时间 |

派生规则：

- `status` 不是独立存储字段，而是从 `ledger.current_state` 映射。
- `provider_success_path` 来自 `ledger.repaired_outputs[*:provider_path]`。
- `available_actions` 由状态机决定，不允许前端自造。

## 3. Events 与 Artifacts

### 3.1 Event Item

契约名：`AgentTaskEventItem`

- strict：否
- additional properties：否
- normalization / adapter：无，直接从 `RunEvent` 转换

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `event_id` | `string` | 是 | 事件主键 |
| `run_id` | `string` | 是 | 所属 run |
| `state` | `RunState` | 是 | 状态机节点 |
| `status` | `RunEventStatus` | 是 | 事件类型 |
| `message` | `string` | 是 | 展示文案 |
| `actor` | `string \| null` | 否 | 事件发起方 |
| `detail` | `object \| null` | 否 | 允许任意键值，当前主要放 stage / kind / fallback metadata |
| `created_at` | `datetime` | 是 | 创建时间 |

### 3.2 Artifact Item

契约名：`AgentTaskArtifactItem`

- strict：否
- additional properties：否
- normalization / adapter：有。若没有 runtime artifact，则服务层会把 `final_artifacts` 退化成 `ref` 记录。

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `artifact_id` | `string` | 是 | artifact 主键 |
| `run_id` | `string` | 是 | 所属 run |
| `artifact_type` | `string` | 是 | 当前 competition artifact 直接使用 task type |
| `title` | `string` | 是 | 展示标题 |
| `payload` | `any` | 否 | runtime artifact 结构化内容 |
| `ref` | `string \| null` | 否 | 当只有 `final_artifacts` 引用时使用 |
| `created_at` | `datetime \| null` | 否 | runtime artifact 时间戳 |

### 3.3 Response 容器

`AgentTaskEventsResponse` 与 `AgentTaskArtifactsResponse` 额外共有：

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `run_id` | `string` | 是 | 当前 run |
| `task_id` | `string` | 是 | 当前实现与 `run_id` 一致 |
| `task_type` | `TaskType \| null` | 否 | 所属任务类型 |
| `current_state` | `RunState \| null` | 否 | 当前状态 |
| `items` | `EventItem[] / ArtifactItem[]` | 是 | 明细列表 |

## 4. 主要 artifact schema

所有 artifact 模型都定义在 `backend/app/schemas/research_runtime.py`，都继承 `ContractBaseModel`。

- strict：否
- additional properties：否
- normalization / adapter：有。`backend/app/agents/output_repair.py` 会先做 wrapper 解包、别名映射、字符串拆分、补字段、删除 extra，再进入 Pydantic 校验。

### 4.1 Recommendation Artifact

契约名：`CompetitionRecommendationArtifact`

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `task_type` | `'competition_recommendation'` | 是 | 固定字面量 |
| `profile_summary` | `string` | 是 | 当前允许 repair 阶段补默认摘要 |
| `recommendations` | `RecommendationItem[]` | 是 | 推荐结果列表 |
| `risk_overview` | `string[]` | 否 | 默认空数组；可从 `risk_notes` 聚合填充 |

`RecommendationItem`

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `competition_id` | `int` | 是 | provider repair 允许从 `id`、`competition.name` 等恢复 |
| `competition_name` | `string` | 是 | provider repair 允许从 `name`、嵌套 `competition` 恢复 |
| `match_score` | `float` | 是 | provider repair 允许从 `score` 别名恢复 |
| `reasons` | `string[]` | 否 | 默认空数组 |
| `risk_notes` | `string[]` | 否 | 默认空数组 |
| `focus_tags` | `string[]` | 否 | 默认空数组 |

当前 review gate：

- `recommendations` 不能为空，否则进入 review

### 4.2 Eligibility Artifact

契约名：`CompetitionEligibilityArtifact`

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `task_type` | `'competition_eligibility_check'` | 是 | 固定字面量 |
| `competition_id` | `int` | 是 | 允许从别名恢复 |
| `competition_name` | `string` | 是 | 允许从别名恢复 |
| `eligibility_label` | `'recommended' \| 'borderline' \| 'not_recommended'` | 是 | 固定枚举 |
| `is_eligible` | `boolean` | 是 | Pydantic 会做常规布尔转换 |
| `missing_conditions` | `string[]` | 否 | 默认空数组 |
| `attention_points` | `string[]` | 否 | 默认空数组 |
| `rationale` | `string[]` | 否 | 默认空数组 |

当前 review gate：

- `rationale` 不能为空
- `attention_points` 不能为空

### 4.3 Timeline Artifact

契约名：`CompetitionTimelineArtifact`

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `task_type` | `'competition_timeline_plan'` | 是 | 固定字面量 |
| `competition_id` | `int` | 是 | 允许从别名恢复 |
| `competition_name` | `string` | 是 | 允许从别名恢复 |
| `deadline` | `string` | 是 | 当前保留为字符串，不做 `datetime` 模型化 |
| `preparation_checklist` | `string[]` | 否 | 默认空数组 |
| `milestones` | `TimelineMilestone[]` | 否 | 默认空数组 |
| `stage_plan` | `string[]` | 否 | 默认空数组 |
| `reverse_schedule` | `string[]` | 否 | 默认空数组 |

`TimelineMilestone`

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `stage` | `string` | 是 | 阶段名 |
| `due_at` | `string` | 是 | ISO 日期字符串 |
| `goals` | `string[]` | 否 | 默认空数组 |
| `deliverables` | `string[]` | 否 | 默认空数组 |

当前 review gate：

- `preparation_checklist` 不能为空
- `milestones` 不能为空
- `stage_plan` 不能为空

## 5. 前端 payload adapter 关键输入 / 输出

契约名：`buildSimpleTaskRequest(taskType, drafts, competitions)`

- 定义位置：`frontend/src/features/agent/input_adapter.ts`
- strict：不适用（TypeScript 编译期类型，不做运行时 schema 校验）
- additional properties：不适用
- normalization / adapter：有

共有 normalization：

- `splitTags()`：按换行 / 英文逗号 / 中文逗号切分并统一转小写
- `resolveCompetitionSelection()`：支持纯数字 `competition_id`、精确名称匹配
- `searchCompetitionSuggestions()`：仅用于 UI 建议，不是后端 contract
- `createAttachmentMetadata()`：只产出元数据，不上传文件

### 5.1 `competition_recommendation`

| Simple 输入 | 输出到 canonical payload |
| --- | --- |
| `direction` | `payload.profile.direction` |
| `grade` | `payload.profile.grade` |
| `abilities` | `payload.profile.ability_tags` |
| `preference_tags` | `payload.profile.preference_tags` |
| `extra_notes` | `payload.profile.extra_notes` |
| `attachments[]` | `payload.attachments` |

输出契约：`AgentTaskCreateRequest`

- `task_type = competition_recommendation`
- `objective` 自动生成
- `dry_run = false`

### 5.2 `competition_eligibility_check`

| Simple 输入 | 输出到 canonical payload |
| --- | --- |
| `competition_query` + `competitions[]` | 解析到 `payload.competition_id` |
| `grade` | `payload.profile.grade` |
| `achievements` + `prerequisites` | 合并拆分到 `payload.profile.ability_tags` |
| `achievements` | `payload.profile.achievements` |
| `prerequisites` | `payload.profile.prerequisites` |
| `team_mode` | `payload.profile.preference_tags = [team_mode]` |
| `extra_notes` | `payload.profile.extra_notes` |
| `attachments[]` | `payload.attachments` |

输出契约：`AgentTaskCreateRequest`

- `task_type = competition_eligibility_check`
- `objective` 自动生成
- 后端不会再帮用户“猜测” `competition_id`

### 5.3 `competition_timeline_plan`

| Simple 输入 | 输出到 canonical payload |
| --- | --- |
| `competition_query` + `competitions[]` | 解析到 `payload.competition_id` |
| `deadline` | `payload.deadline` |
| `weekly_hours` | `payload.constraints.available_hours_per_week` |
| `current_stage` | `payload.constraints.notes[]` |
| `goals_or_constraints` | `payload.constraints.notes[]` |
| `extra_notes` | `payload.constraints.notes[]` |
| `attachments[]` | `payload.attachments` |

输出契约：`AgentTaskCreateRequest`

- `task_type = competition_timeline_plan`
- `objective` 自动生成
- `deadline` 保持字符串形态直接下发

### 5.4 Advanced Mode

Advanced Mode 直接提交：

- `task_type`
- `objective`
- `payload`
- `dry_run = false`

当前只有 JSON.parse 级别校验，没有前端运行时 schema validator。

## 6. Crawler placeholder request / result schema

这些 schema 已有代码实现，但当前仅作为 scaffold，不接入 API 和主 runtime。

- 定义位置：`backend/app/crawler/schemas.py`
- strict：否
- additional properties：否
- normalization / adapter：无
- 实现状态：占位

### 6.1 `CrawlRequest`

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `request_id` | `string` | 是 | 请求主键 |
| `source` | `string` | 是 | 来源标识 |
| `target` | `string` | 是 | 目标站点或目标域 |
| `entrypoint` | `string` | 是 | 入口 URL |
| `metadata` | `object` | 否 | 默认空对象 |

### 6.2 `CrawlDocument`

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `document_id` | `string` | 是 | 文档主键 |
| `source` | `string` | 是 | 来源标识 |
| `title` | `string \| null` | 否 | 文档标题 |
| `content` | `string` | 否 | 默认空字符串 |
| `metadata` | `object` | 否 | 默认空对象 |

### 6.3 `CrawlResult`

| 字段 | 类型 | Required | 说明 |
| --- | --- | --- | --- |
| `request_id` | `string` | 是 | 对应 `CrawlRequest` |
| `provider` | `string` | 是 | 当前固定 `placeholder` |
| `status` | `'placeholder' \| 'not_implemented'` | 是 | 当前实际返回 `not_implemented` |
| `documents` | `CrawlDocument[]` | 否 | 默认空数组 |
| `notes` | `string[]` | 否 | 默认空数组 |
| `warnings` | `string[]` | 否 | 默认空数组 |
| `created_at` | `datetime` | 否 | 默认当前 UTC 时间 |
