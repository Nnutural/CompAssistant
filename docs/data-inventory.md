# 数据资产台账

本台账只描述仓库当前已经出现、已经依赖、或已经被文档显式规划的数据对象，不引入新概念。

状态口径：

- `已实现`：代码路径可达，且当前仓库已经消费或持久化。
- `部分实现`：对象存在，但只覆盖部分链路、部分任务类型，或只有元数据没有完整消费链路。
- `占位`：有 schema / scaffold / placeholder 实现，但未接入主流程。
- `未实现`：文档或配置提到未来边界，仓库中没有真正的数据消费链路。

## 后端 API 与 runtime

| 数据对象 | 所属层 | 当前状态 | 代码位置 | 主要消费者 | 是否持久化 | 是否为 source-of-truth | 影响面 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `AgentTaskCreateRequest` | backend / api | 已实现 | `backend/app/schemas/agent_tasks.py`, `backend/app/api/routes/agent_tasks.py` | `POST /api/agent/tasks`, `ResearchRuntimeService.create_agent_task()` | 否 | 是 | API |
| `AgentTaskStatusResponse` | backend / api | 已实现 | `backend/app/schemas/agent_tasks.py`, `backend/app/services/research_runtime_service.py` | 前端 polling、历史列表、控制动作返回体 | 否（由 ledger 派生） | 是 | API |
| `AgentTaskEventsResponse` / `AgentTaskEventItem` | backend / api | 已实现 | `backend/app/schemas/agent_tasks.py`, `backend/app/agents/run_state.py` | 前端事件时间线、测试 | 是（写入 ledger.events） | 是 | API |
| `AgentTaskArtifactsResponse` / `AgentTaskArtifactItem` | backend / api | 已实现 | `backend/app/schemas/agent_tasks.py`, `backend/app/services/research_runtime_service.py` | 前端 artifact 面板、评测 | 是（写入 ledger.artifacts / final_artifacts） | 是 | API + artifact + eval |
| `AgentTaskHistoryResponse` / `AgentTaskHistoryItem` | backend / api | 已实现 | `backend/app/schemas/agent_tasks.py`, `backend/app/services/research_runtime_service.py` | 前端最近任务列表、路由测试 | 是（由 ledger 列表派生） | 是 | API |
| `AgentTaskCancelRequest` / `AgentTaskReviewRequest` / control 返回体 | backend / api | 已实现 | `backend/app/schemas/agent_tasks.py`, `backend/app/api/routes/agent_tasks.py` | retry / cancel / review 控制接口 | 是（control_records + events） | 是 | API |
| `ResearchLedger` | runtime / storage | 已实现 | `backend/app/schemas/research_runtime.py`, `backend/app/repositories/ledger_repository.py` | `ResearchRuntimeService`、历史/状态/artifact 派生、测试 | 是（`backend/data/research_ledgers/*.json`） | 是 | API + artifact + eval |
| `ResearchLedger` 运行跟踪字段（`events` / `raw_outputs` / `repaired_outputs` / `validation_errors` / `parse_errors` / `control_records`） | runtime | 已实现 | `backend/app/agents/run_state.py`, `backend/app/agents/manager.py` | 路由响应派生、问题定位、评测错误分桶 | 是（ledger 内嵌） | 是 | API + artifact + eval |
| `CompetitionRecommendationArtifact` | runtime / artifact | 已实现 | `backend/app/schemas/research_runtime.py`, `backend/app/agents/competition_recommender.py` | artifact 面板、评测、provider/mode 对齐 | 是（runtime artifact + ledger output） | 是 | artifact + eval |
| `CompetitionEligibilityArtifact` | runtime / artifact | 已实现 | `backend/app/schemas/research_runtime.py`, `backend/app/agents/eligibility_checker.py` | artifact 面板、评测、review 流程 | 是 | 是 | artifact + eval |
| `CompetitionTimelineArtifact` | runtime / artifact | 已实现 | `backend/app/schemas/research_runtime.py`, `backend/app/agents/timeline_planner.py` | artifact 面板、评测 | 是 | 是 | artifact + eval |
| legacy `research_plan` 管线数据（`source_registry` / `evidence_log` / legacy findings） | runtime / legacy | 部分实现 | `backend/app/agents/trend_scout.py`, `backend/app/agents/evidence_scout.py`, `backend/app/agents/critic.py` | 兼容 `POST /api/research-runtime/run`、旧 contract 示例、部分单测 | 是（ledger 内嵌） | 是（仅 legacy 路径） | API + eval |

## 前端输入层与 UI 状态

| 数据对象 | 所属层 | 当前状态 | 代码位置 | 主要消费者 | 是否持久化 | 是否为 source-of-truth | 影响面 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Simple Mode 草稿与 payload adapter | frontend | 已实现 | `frontend/src/features/agent/input_adapter.ts`, `frontend/src/features/agent/components/TaskForm.vue` | Agent 面板表单、payload 预览 | 否 | 否（后端 Pydantic 才是最终 SoT） | API |
| Advanced Mode `objective + payload JSON` 草稿 | frontend | 已实现 | `frontend/src/features/agent/config.ts`, `frontend/src/features/agent/components/TaskForm.vue` | 调试、演示、E2E | 否 | 否 | API |
| `payload.attachments` 元数据 | frontend / request | 部分实现 | `frontend/src/features/agent/input_adapter.ts`, `frontend/src/features/agent/components/TaskForm.vue` | 表单、payload 预览、ledger.request_payload 样本 | 是（作为请求 JSON 一部分被 ledger 记录） | 否 | API |

## 本地静态数据集

| 数据对象 | 所属层 | 当前状态 | 代码位置 | 主要消费者 | 是否持久化 | 是否为 source-of-truth | 影响面 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 竞赛目录原始数据 `competitions.json` | backend / storage | 已实现 | `backend/data/competitions.json`, `backend/app/api/routes/competitions.py` | `GET /api/competitions`、runtime 本地工具、前端赛事选择 | 是（静态 JSON） | 是 | API + artifact + eval |
| 竞赛扩展画像 `competitions_enriched.json` | backend / runtime | 已实现 | `backend/data/competitions_enriched.json`, `backend/app/tools/competition_runtime.py` | 推荐、资格判断、时间线工具 | 是（静态 JSON） | 是 | artifact + eval |
| 资格规则 `eligibility_rules.json` | backend / runtime | 已实现 | `backend/data/eligibility_rules.json`, `backend/app/tools/competition_runtime.py` | `check_eligibility_rules()`、评测对照 | 是（静态 JSON） | 是 | artifact + eval |
| 推荐打分规则 `recommendation_rubric.json` | backend / runtime | 已实现 | `backend/data/recommendation_rubric.json`, `backend/app/tools/competition_runtime.py` | 推荐排序、评测质量分 | 是（静态 JSON） | 是 | artifact + eval |
| 时间线模板 `timeline_templates.json` | backend / runtime | 已实现 | `backend/data/timeline_templates.json`, `backend/app/tools/competition_runtime.py` | `build_timeline_template()`、时间线评测 | 是（静态 JSON） | 是 | artifact + eval |

## 本地持久化、provider 附着数据与配置

| 数据对象 | 所属层 | 当前状态 | 代码位置 | 主要消费者 | 是否持久化 | 是否为 source-of-truth | 影响面 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 运行 ledger 文件 `research_ledgers/*.json` | storage | 已实现 | `backend/data/research_ledgers/`, `backend/app/repositories/ledger_repository.py` | 状态查询、历史列表、artifact 派生、回归样本 | 是（JSON 文件） | 是 | API + artifact + eval |
| Agents SDK session SQLite `research_runtime_sessions.sqlite3` | storage / provider | 已实现 | `backend/data/research_runtime_sessions.sqlite3`, `backend/app/agents/runtime_tools.py` | `AgentsSDKResearchRuntime`, `ResearchAgentFactory` | 是（SQLite） | 是（仅 provider session state） | provider runtime |
| Ark provider 输出（structured / plain JSON fallback） | runtime / provider | 部分实现 | `backend/app/agents/agent_factory.py`, `backend/app/agents/output_repair.py` | `agents_sdk` 路径、评测、debug 脚本 | 部分持久化（写入 `raw_outputs` / `repaired_outputs` / issue） | 否 | artifact + eval |
| provider 执行语义字段（`requested_runtime_mode` / `effective_runtime_mode` / `provider_success_path` / `used_mock_fallback` / `fallback_reason`） | runtime / provider | 已实现 | `backend/app/services/research_runtime_service.py`, `backend/app/schemas/agent_tasks.py` | 前端状态面板、评测、operator guide | 是（ledger + API 派生） | 是 | API + eval |
| MySQL 配置与 `sqlalchemy_database_uri` | config | 部分实现 | `backend/app/core/config.py`, `backend/.env.example` | `Settings`，但当前请求流程未消费数据库层 | 否（配置来源为 env） | 是（仅配置定义） | config |

## 测试、评测与文档契约数据

| 数据对象 | 所属层 | 当前状态 | 代码位置 | 主要消费者 | 是否持久化 | 是否为 source-of-truth | 影响面 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 评测样本集 `backend/data/evals/*.json` | eval | 已实现 | `backend/data/evals/`, `backend/app/services/evaluation_service.py` | `run_eval.py`, `run_eval_agents_sdk.py`, 回归测试 | 是（静态 JSON） | 是（对评测链路） | eval |
| `EvaluationReport` / `EvaluationCaseResult` | eval | 已实现 | `backend/app/schemas/evaluation.py`, `backend/app/services/evaluation_service.py` | CLI 报告、评测单测 | 否（默认进程内生成） | 是 | eval |
| 前端 E2E 固定样例 `frontend/e2e/fixtures/agent-demo-cases.json` | test / e2e | 已实现 | `frontend/e2e/fixtures/agent-demo-cases.json` | Playwright smoke | 是（静态 JSON） | 是（对 E2E） | eval / demo |
| 文档 schema 与 example JSON（`docs/schemas/*`, `docs/examples/*`） | docs / contracts | 已实现 | `docs/schemas/`, `docs/examples/`, `backend/app/tests/test_research_runtime_contracts.py` | 文档、contract 测试、legacy 示例 | 是（静态 JSON） | 否（Pydantic model 才是最终 SoT） | docs + test |

## 占位与未实现边界

| 数据对象 | 所属层 | 当前状态 | 代码位置 | 主要消费者 | 是否持久化 | 是否为 source-of-truth | 影响面 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Crawler placeholder contract（`CrawlRequest` / `CrawlResult` / `CrawlDocument`） | crawler | 占位 | `backend/app/crawler/schemas.py`, `backend/app/crawler/service.py` | scaffold 单测、未来 crawler 边界 | 仅内存 placeholder store | 是（对占位 scaffold） | planned |
| 真实 crawler 抓取文档 / 站点原始页 | crawler | 未实现 | `docs/ai-crawler-placeholder.md`, `backend/app/crawler/README.md` | 当前无消费者 | 否 | 否 | planned |
| 附件二进制内容 / 上传物 | frontend / storage | 未实现 | `docs/frontend-integration.md`, `frontend/src/features/agent/components/TaskForm.vue` | 当前无消费者 | 否 | 否 | planned |
| 数据库中的 run / task / artifact 记录 | storage / database | 未实现 | `backend/app/core/config.py`, `backend/AGENTS.md`, `README.md` | 当前无消费者 | 否 | 否 | planned |
