# Data Contracts

本文件记录 Phase 5H 之后当前仓库里与本地知识闭环有关的稳定契约。

## 1. 契约边界

- 现有任务 API、runtime ledger、competition artifact 契约不变。
- 本地知识链路仍是实验性能力，只通过 retrieval service 暴露给智能体。
- 智能体不得直接读取原始网页、raw 文件或 crawler 中间产物。

## 2. Phase 5H taxonomy 契约

位置：`backend/app/crawler/taxonomy.py`

### 内容类别 `source_type`

- `national_policy`
- `law_regulation`
- `social_hotspot`
- `employment_recruitment`
- `fund_guide`
- `approved_project`
- `competition_info`
- `award_winning_work`
- `excellent_template`
- `experience_sharing`

### 渠道类别 `source_channel`

- `public_web`
- `wechat_official_account`
- `manual_import`
- `local_file`

### 实现状态 `implementation_status`

- `implemented`
- `importer`
- `placeholder`
- `planned`

## 3. 三层文档契约

位置：`backend/app/crawler/schemas.py`

### `RawDocument`

- `doc_id`: required
- `source_type`: required，内容类别
- `source_channel`: required，渠道类别
- `source_name`: required
- `implementation_status`: required
- `url`: required
- `fetch_method`: required
- `raw_content_type`: required
- `raw_text`: optional
- `raw_ref`: optional
- `fetched_at`: required datetime
- `metadata`: required object，默认 `{}`

校验规则：

- extra fields forbidden
- `raw_text` 和 `raw_ref` 至少存在一个

### `NormalizedDocument`

- `doc_id`
- `source_type`
- `source_channel`
- `source_name`
- `implementation_status`
- `url`
- `title`
- `publish_time`
- `content_text`
- `tags`
- `region`
- `school_or_org`
- `raw_ref`
- `checksum`
- `language`
- `collected_at`
- `normalized_metadata`

校验规则：

- extra fields forbidden
- `tags` 去重
- `title`、`content_text`、`raw_ref`、`checksum` 为必填

### `KnowledgeRecord`

- `record_id`
- `doc_id`
- `title`
- `summary`
- `content_text`
- `source_type`
- `source_channel`
- `source_name`
- `implementation_status`
- `tags`
- `publish_time`
- `url`
- `searchable_text`
- `indexed_at`

约束：

- `searchable_text` 由 `title + summary + content_text + tags` 组成
- 进入检索层前必须已经标准化

## 4. Source manifest 契约

位置：`backend/app/crawler/source_manifest.py`

### `SourceManifestEntry`

- `source_id`
- `source_type`
- `source_channel`
- `source_name`
- `implementation_status`
- `access_strategy`
- `entrypoint`
- `description`
- `notes`

说明：

- 这是 Phase 5H 的类别覆盖台账，不等同于仓库总数据台账 `docs/data-manifest.json`
- 详细文档镜像位于 `docs/data-source-manifest.json`

## 5. Retrieval 契约

位置：`backend/app/retrieval/schemas.py`

### `DocumentSearchFilters`

- `source_type`: optional single category
- `source_types`: optional category array
- `source_channel`: optional single channel
- `source_channels`: optional channel array
- `source_name`: optional
- `implementation_status`: optional single status
- `implementation_statuses`: optional status array
- `tags`: optional array

### `DocumentSearchHit`

- `record_id`
- `doc_id`
- `title`
- `summary`
- `source_type`
- `source_channel`
- `source_name`
- `implementation_status`
- `tags`
- `publish_time`
- `url`
- `score`

## 6. 仍然不变的边界

- 不新增任务类型
- 不重构主 runtime
- 不修改 competitions API 契约
- 不修改前端主流程契约
- 不引入 Playwright 抓取主线
- 不引入登录、验证码、代理、反爬绕过
- 不引入 Redis、Celery、向量数据库、RAG、WebSocket
