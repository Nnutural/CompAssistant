# 数据来源台账

本页只描述“数据从哪里来”，不把所有对象都重复展开。

补充说明：

- 本仓库未发现 Notion 导出的数据源或 Notion API 接入代码，本次盘点仅以仓库内 `README.md`、`docs/`、后端/前端代码和本地数据文件为准。
- `provider`、`crawler`、未来数据库都按“附着资源（attached resources）”理解，不是当前仓库的本地 source-of-truth。

## 内部静态数据

| 来源名称 | 实现状态 | 接入方式（当前 / 规划） | 凭证 / 配置来源 | 刷新方式 | 风险说明 |
| --- | --- | --- | --- | --- | --- |
| `backend/data/competitions.json` | 已实现 | 当前由 `competitions` API 与 runtime 本地工具直接读取 | 文件路径配置，无凭证 | 手动维护 | 竞赛字段没有独立 schema 文件；deadline 依赖字符串可解析；人工更新容易漂移 |
| `backend/data/competitions_enriched.json` | 已实现 | 当前由 `competition_runtime.py` 直接读取 | 文件路径配置，无凭证 | 手动维护 | 与 `competitions.json` 的 `id` / `field` 需要人工保持一致 |
| `backend/data/eligibility_rules.json` | 已实现 | 当前由 `check_eligibility_rules()` 读取 | 文件路径配置，无凭证 | 手动维护 | 规则解释性强，但没有独立版本化测试来保证业务语义稳定 |
| `backend/data/recommendation_rubric.json` | 已实现 | 当前由推荐排序与 eval 质量评分共享读取 | 文件路径配置，无凭证 | 手动维护 | 同一份 rubric 同时影响排序与 eval，误改会同时改变结果和评分基线 |
| `backend/data/timeline_templates.json` | 已实现 | 当前由 `build_timeline_template()` 读取 | 文件路径配置，无凭证 | 手动维护 | 模板结构由代码隐式约束，缺少独立 schema 校验 |

## 本地运行时生成数据

| 来源名称 | 实现状态 | 接入方式（当前 / 规划） | 凭证 / 配置来源 | 刷新方式 | 风险说明 |
| --- | --- | --- | --- | --- | --- |
| `backend/data/research_ledgers/*.json` | 已实现 | 当前由 `LedgerRepository` 原子写入 / 读取 | 存储目录配置，可由 `LedgerRepository(storage_dir=...)` 覆盖 | 运行时生成 | JSON ledger 同时承担状态机、artifact、历史与调试信息，未来若接数据库边界要定义清楚 |
| `ResearchLedger.raw_outputs` / `repaired_outputs` / `validation_errors` / `parse_errors` | 已实现 | 当前嵌入 ledger 持久化 | 无额外凭证 | 运行时生成 | provider 输出只做“部分持久化”，不会保留完整 SDK 原始响应对象 |
| `backend/data/research_runtime_sessions.sqlite3` | 已实现 | 当前由 `resolve_session_db_path()` 解析并供 Agents SDK session memory 使用 | 环境变量 `RESEARCH_RUNTIME_SESSION_DB` 或默认本地路径 | 运行时生成 | 会累积 provider 会话记忆；跨 run 污染风险已通过每 run 唯一 session id 缓解，但文件仍需定期治理 |
| `requested_runtime_mode` / `effective_runtime_mode` / `provider_success_path` / `used_mock_fallback` | 已实现 | 当前由 service 从 runtime 结果与 ledger 派生 | 无额外凭证 | 运行时生成 | 如果前端只看 `completed` 而不看这些字段，会误判 provider 是否真实成功 |

## provider 返回数据

| 来源名称 | 实现状态 | 接入方式（当前 / 规划） | 凭证 / 配置来源 | 刷新方式 | 风险说明 |
| --- | --- | --- | --- | --- | --- |
| Ark Agents SDK structured output | 已实现 | 当前由 `AgentsSDKResearchRuntime` + `ResearchAgentFactory` 调用，之后进入 repair / validate | 环境变量 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_DEFAULT_MODEL` | 运行时生成 | provider schema 漂移、turn budget、timeout、availability 都会直接影响成功率 |
| Ark provider plain JSON fallback output | 已实现 | 当前在 structured 失败后自动尝试 fallback，再走同一套 repair / validate | 同上 | 运行时生成 | 成功并不等于 structured 直出；必须和 `provider_success_path` 一起解释 |
| provider 异常文本 / parse 错误 / validation issue | 已实现 | 当前写入 ledger issue 列表与 eval error buckets | 同上 | 运行时生成 | 只保留归因结果，不保留完整 HTTP 级响应；适合诊断，不适合审计复现 |
| provider schema debug payload | 部分实现 | 仅在 `schema_debug_enabled` 时写入 ledger | 环境变量 / service 配置 | 运行时生成 | 默认关闭；不能假设生产或 CI 一定存在这批数据 |

## 人工维护与用户输入数据

| 来源名称 | 实现状态 | 接入方式（当前 / 规划） | 凭证 / 配置来源 | 刷新方式 | 风险说明 |
| --- | --- | --- | --- | --- | --- |
| 前端 Simple Mode 表单数据 | 已实现 | 当前由 `input_adapter.ts` 转成 canonical `AgentTaskCreateRequest` | 浏览器内状态，无凭证 | 用户每次提交时生成 | adapter 会做 tag split / competition query 解析；如果规则变更，前后端要一起更新 |
| 前端 Advanced Mode `objective + payload JSON` | 已实现 | 当前直接作为 task API 请求体核心内容提交 | 浏览器内状态，无凭证 | 用户每次提交时生成 | 当前没有前端 runtime schema 校验，错误主要在后端 Pydantic 边界暴露 |
| `payload.attachments` 元数据 | 部分实现 | 当前只记录 `name` / `kind` / `mime_type` / `local_ref` 到请求 JSON | 浏览器本地文件元数据，无上传凭证 | 用户每次选择文件时生成 | 只有元数据，没有文件本体；很容易被误认为“已支持附件消费” |
| `backend/.env` / `backend/.env.example` 中的 runtime 配置 | 已实现 | 当前由 `Settings(BaseSettings)` 读取 | 环境变量 / `.env` 模板 | 手动维护 | provider、session DB、timeout 与默认 model 都依赖它；配置漂移会直接影响运行解释 |
| MySQL 配置项（`MYSQL_*`） | 部分实现 | 仅在 `Settings` 中定义，当前请求流程未真正使用 | 环境变量 / `.env` 模板 | 手动维护 | 容易让维护者误以为数据库已接入；当前必须明确标记为“配置存在但链路未接入” |

## 测试 / 评测数据

| 来源名称 | 实现状态 | 接入方式（当前 / 规划） | 凭证 / 配置来源 | 刷新方式 | 风险说明 |
| --- | --- | --- | --- | --- | --- |
| `backend/data/evals/*.json` | 已实现 | 当前由 `load_evaluation_cases()` 加载 | 文件路径配置，无凭证 | 手动维护 | eval case 会同时定义字段完备性和质量门槛；改动要同步回归预期 |
| `frontend/e2e/fixtures/agent-demo-cases.json` | 已实现 | 当前由 Playwright smoke 使用 | 文件路径配置，无凭证 | 手动维护 | 演示样例和真实 runtime 行为可能逐步偏离，需定期校对 |
| `docs/examples/*.json` 与 `docs/schemas/*.json` | 已实现 | 当前用于 contract 文档与单测 | 文件路径配置，无凭证 | 手动维护 | 当前覆盖 legacy runtime contract 更充分，新 task API DTO 还没有对应 JSON Schema 文件 |
| 测试时临时 ledger 目录 | 已实现 | 当前由多处单测使用 `tempfile.TemporaryDirectory()` 构造 | 无凭证 | 运行时生成 | 测试只覆盖文件可解析与部分路由语义，不代表生产级存储治理已完成 |

## 未来规划中的外部来源

| 来源名称 | 实现状态 | 接入方式（当前 / 规划） | 凭证 / 配置来源 | 刷新方式 | 风险说明 |
| --- | --- | --- | --- | --- | --- |
| 真实 crawler 站点原始数据 | 未实现 | 当前仅有 `backend/app/crawler/` scaffold；未来按 source adapter / pipeline / store 接入 | 未来应走环境变量或等价配置注入 | 未定义 | 当前没有真实 source，也没有 schema 稳定性保证，不能把 scaffold 误判为已接入 |
| 数据库中的 task / run / artifact / history 记录 | 未实现 | 当前没有数据库仓储实现；未来若接入需替换或桥接 `LedgerRepository` | 未来应走 DSN / 账号 / 密钥配置 | 未定义 | 当前 JSON ledger 与未来数据库的边界尚未定义清楚，是后续工程化重点风险 |
| 附件文件内容 / 对象存储 | 未实现 | 当前仅保存元数据；未来若接入需要单独的上传、存储、鉴权链路 | 未来应走对象存储或文件服务配置 | 未定义 | 现阶段只有 metadata，没有文件本体，也没有合规与容量策略 |
| 真正的外部竞赛源站 / crawler 同步源 | 未实现 | 当前竞赛数据完全靠仓库内 JSON；未来才会考虑同步 | 未来应走 crawler/provider 配置 | 未定义 | 一旦引入外部源，`competitions.json` 与抓取结果谁是 SoT 必须先定义 |
