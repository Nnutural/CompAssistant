# 数据工程规则

本页是当前仓库的数据工程约束。目标不是“设计理想架构”，而是让现有 JSON + FastAPI + agent runtime + eval 体系可持续维护。

## 1. Source-of-Truth 规则

1. 后端 Pydantic 模型是 API / runtime 契约的最终 source-of-truth。
   当前主要指 `backend/app/schemas/agent_tasks.py` 与 `backend/app/schemas/research_runtime.py`。
1. 前端 `frontend/src/types/agent.ts` 是镜像类型，不得先于后端 schema 自行发明字段。
1. `backend/data/competitions.json`、`competitions_enriched.json`、`eligibility_rules.json`、`recommendation_rubric.json`、`timeline_templates.json` 是当前竞赛本地知识库的 source-of-truth。
1. `ResearchLedger` 是当前每个 run 的本地持久化 source-of-truth。
   `status`、`history`、`events`、`artifacts`、`fallback` 解释都必须能回落到 ledger。
1. provider 返回内容、crawler 未来返回内容、数据库未来记录都不是当前仓库的 source-of-truth。
   它们都是附着资源，必须经过本地 contract 校验后才能进入 ledger / artifact。

## 2. 允许 normalization 的边界

允许 normalization 的位置：

1. provider 产出的 competition artifact 在进入最终 Pydantic 校验前，允许经过 `backend/app/agents/output_repair.py` 做有限修复。
1. 前端 Simple Mode 允许把自然输入映射成 canonical payload。
1. `ResearchRuntimeService` 允许补默认 `objective`、`task_id`、`session_id`。

当前允许的 provider normalization 类型：

1. wrapper 解包：`result` / `data` / `output` / `artifact` / `final_output`
1. 别名映射：`id -> competition_id`、`name -> competition_name`、`score -> match_score`
1. 字符串拆分为列表：`risk_notes`、`reasons`、`focus_tags`
1. 缺省补全：`profile_summary`、`risk_overview`
1. 从本地 `competitions.json` 反查 `competition_id`
1. 删除 artifact schema 不接受的 extra fields

不允许静默修正的字段：

1. `task_type`
1. `run_id` / `task_id`
1. `session_id`
1. `ledger_id`
1. `ReviewDecision`
1. `ControlAction`
1. `TaskRunStatus` / `RunState`
1. 用户请求边界上的 `competition_id`

说明：

- `competition_id` 可以在前端 Simple Mode 提交前解析得到，但一旦进入后端 API，请求本身就必须是 canonical 值。
- `payload.attachments` 当前只允许作为 metadata，不得假装系统已支持文件内容消费。

## 3. 契约与实现变更顺序

1. 先更新后端 schema。
1. 再更新前端类型镜像与 adapter。
1. 再更新 `docs/data-contracts.md`、`docs/data-inventory.md`、`docs/data-manifest.json`。
1. 最后才改实现与测试。

禁止顺序：

1. 先改路由返回体，再补 schema / docs
1. 先在前端消费新字段，再让后端“补齐”
1. 先把 planned source 写成文档里的“已接入”

## 4. 新增数据源时必须补齐的内容

新增任意数据源时，至少补以下内容：

1. `docs/data-inventory.md` 新增数据对象条目
1. `docs/data-sources.md` 新增来源条目
1. `docs/data-manifest.json` 新增机器可读条目
1. 说明接入方式、刷新方式、风险、source-of-truth
1. 说明是 `已实现`、`部分实现`、`占位` 还是 `未实现`

如果新增的是外部资源，还必须补：

1. 配置项说明
1. 最小失败语义
1. mock / live / eval 的隔离方式

## 5. 新增 schema 时必须补的测试

新增或修改核心 schema 时，至少补这些测试中的对应一项：

1. Pydantic model validation 单测
1. 路由 contract 测试
1. ledger 序列化 / 反序列化测试
1. eval 样本或 fixture 更新
1. 若存在文档 schema / example，则同步更新文档 contract 测试

最低要求：

- 任何会影响 API 返回体、artifact payload、eval 评分字段的 schema 变更，都不能只改实现不改测试。

## 6. 附着资源（attached resources）规则

以下资源一律视为附着资源：

1. Ark / provider
1. crawler / source adapter
1. 数据库
1. 对象存储 / 文件存储
1. 未来队列、worker、缓存

约束：

1. 配置必须通过环境变量或等价配置注入
1. 不能把密钥、账号、站点凭证写死在业务代码中
1. 代码里的默认值只能作为本地开发兼容，不能视为生产配置策略
1. provider / crawler / database 的接入状态必须在文档中显式标注

当前仓库中特别需要注意：

- `backend/app/core/config.py` 里存在 MySQL 默认配置，但当前请求流程并未真正使用数据库层。
- 这类“配置存在但链路未接入”的对象必须在文档中继续标为 `部分实现` 或 `未实现`，不能标成已接入。

## 7. 配置与业务代码分离

1. provider 模型名、base URL、timeout、session DB 路径属于配置，不属于业务规则。
1. 竞赛匹配权重、资格规则、timeline 模板属于数据，不属于硬编码逻辑。
1. 前端轮询间隔、历史分页大小属于 UI 配置，不属于 API contract。

要求：

1. 改配置时优先改配置文件 / env 模板 / 文档，不要把新常量散落进实现代码。
1. 业务代码只能消费配置，不能重新定义另一套命名。

## 8. Mock / Eval / Provider 数据隔离

必须始终区分：

1. mock runtime 结果
1. provider 真实结果
1. provider 失败后 mock fallback 的结果
1. eval 数据集
1. E2E / demo fixture

禁止混用结论：

1. `completed` 不等于 provider 直出成功
1. mock fallback 结果不能写成“真实 Ark 成功”
1. eval case 的期望字段不能反过来当生产知识库
1. E2E 演示样例不能当业务事实数据

必须保留的解释字段：

1. `requested_runtime_mode`
1. `effective_runtime_mode`
1. `provider_success_path`
1. `used_mock_fallback`
1. `fallback_reason`

## 9. 存储边界规则

1. 当前 JSON ledger 是正式存储边界，不是临时调试残留。
1. 若未来接数据库，必须先定义 JSON ledger 与数据库记录的迁移 / 并存 / 回放策略。
1. 若未来接 crawler，必须先定义抓取原始文档、归一化结果、最终可消费 artifact 之间的边界。
1. 若未来接附件上传，必须先定义 metadata 与 binary content 的边界。

## 10. 状态标注规则

1. `已实现` 只用于代码路径真实可达的对象或来源。
1. `部分实现` 用于只覆盖部分链路、部分任务类型、或只有 metadata 的对象。
1. `占位` 用于 scaffold / placeholder provider / placeholder result。
1. `未实现` 用于当前仓库只在文档、README、配置边界里出现的未来对象。

任何未实现的数据源都必须明确标注为 `planned` / `placeholder`，不得伪装成已实现。
