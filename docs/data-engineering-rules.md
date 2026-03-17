# Data Engineering Rules

本仓库仍然优先保证现有 competition assistant 主系统稳定。Phase 5H 的数据扩展必须保持小范围、可解释、可回滚。

## 1. Source-of-truth 规则

- 任务 API、runtime、competition 数据契约仍以 backend Pydantic 和现有本地 JSON 为准。
- 本地知识的数据分类和来源台账以 `backend/app/crawler/taxonomy.py` 与 `backend/app/crawler/source_manifest.py` 为代码真源。
- `docs/data-source-manifest.json` 是文档镜像，不替代代码真源。
- 智能体只能消费 `KnowledgeRecord` 或 `DocumentSearchHit`。

## 2. Phase 5H 范围规则

本轮允许：

- 10 类内容类别全部进入 taxonomy / manifest / docs / code 结构
- 公开静态 HTTP 获取
- 本地 JSON / CSV / Markdown / TXT importer
- 微信公众号文章手动导入
- 文件系统存储 raw / normalized
- SQLite + FTS5 检索
- 第 2 个智能体的 feature-flagged retrieval 接入

本轮禁止：

- Playwright 作为主抓取链路
- 登录、验证码、代理、反爬绕过
- 多站点调度系统
- Redis / Celery / WebSocket / 向量数据库 / RAG
- MySQL / PostgreSQL 迁移
- 改动 competitions API、task API、前端主流程

## 3. 渠道与类别规则

- `source_type` 只表示内容类别，不得混入渠道含义。
- `source_channel` 只表示渠道，不得混入内容类别。
- `implementation_status` 必须诚实反映 `implemented / importer / placeholder / planned`。
- 任何未落地的来源不得伪装成 `implemented`。

## 4. 存储规则

- `RawDocument` 落本地文件系统。
- `NormalizedDocument` 落本地文件系统。
- `KnowledgeRecord` 落 SQLite 索引。
- 若 FTS5 不可用，可退化为 LIKE 检索，但必须保留兼容说明。
- 遗留旧 schema payload 允许在读取层跳过，不得影响主流程。

## 5. 标准化规则

- `RawDocument` 必须包含 `source_type`、`source_channel`、`implementation_status`。
- `NormalizedDocument` 必须包含清洗后的 `title`、`content_text`、`checksum`、`language`。
- `KnowledgeRecord.searchable_text` 必须由 `title + summary + content_text + tags` 构成。
- Markdown/TXT/JSON/CSV 导入后必须走同一条标准化链路。

## 6. 智能体接入规则

- 智能体不得直接读网页和 raw 文件。
- 本地知识接入必须通过 retrieval service。
- 任何 agent grounding 必须通过 feature flag 或实验性服务边界隔离。
- 当前允许接入的 agent 仅限 `eligibility-checker` 和 `competition-recommender`。

## 7. 测试与文档同步规则

当 taxonomy、source manifest、importer、retrieval 或 agent grounding 发生变化时，必须同步更新：

- `docs/data-inventory.md`
- `docs/data-sources.md`
- `docs/data-contracts.md`
- `docs/data-engineering-rules.md`
- `docs/current-state.md`
- `docs/ai-crawler-placeholder.md`
- `docs/data-manifest.json`
- `docs/data-source-manifest.json`

并保持以下测试覆盖：

- schema 构造/校验
- source manifest 一致性
- importer
- normalize pipeline
- sqlite index upsert/search
- retrieval service 多类别过滤
- 至少 2 个智能体的本地知识 grounding
