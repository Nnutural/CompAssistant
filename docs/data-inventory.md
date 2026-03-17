# Data Inventory

状态标签：

- `implemented`: 代码和运行样例已落地
- `partial`: 已接入但只覆盖部分消费路径
- `placeholder`: 只保留占位边界
- `unimplemented`: 仍未实现

## 1. 主系统核心数据

| Object | Layer | Status | Source of truth | Persisted | Main consumers |
| --- | --- | --- | --- | --- | --- |
| `AgentTaskCreateRequest` | backend api | implemented | backend Pydantic | no | task API |
| `AgentTaskStatusResponse` | backend api | implemented | backend Pydantic | derived | task API / frontend |
| `ResearchLedger` | runtime | implemented | backend Pydantic | yes | runtime / history / artifacts |
| competition runtime artifacts | runtime | implemented | backend Pydantic | yes | runtime / evaluation / frontend |
| competitions static datasets | storage | implemented | local JSON | yes | competitions API / runtime tools |

## 2. Phase 5H 本地知识数据

| Object | Layer | Status | Source of truth | Persisted | Main consumers |
| --- | --- | --- | --- | --- | --- |
| `crawler_source_taxonomy` | crawler | implemented | `backend/app/crawler/taxonomy.py` | no | crawler / retrieval |
| `SourceManifestEntry` | crawler | implemented | `backend/app/crawler/source_manifest.py` | docs mirror | build script / docs / tests |
| `RawDocument` | crawler | implemented | `backend/app/crawler/schemas.py` | yes | provider / importer / ingestion |
| `NormalizedDocument` | crawler | implemented | `backend/app/crawler/schemas.py` | yes | normalize pipeline / filesystem store |
| `KnowledgeRecord` | retrieval | implemented | `backend/app/crawler/schemas.py` | yes | sqlite index / retrieval service |
| `FileDocumentImporter` | crawler importer | implemented | code | no | template / experience / wechat import |
| `StructuredDataImporter` | crawler importer | implemented | code | no | hotspot / awards / competition data |
| `WeChatArticleImporter` | crawler importer | implemented | code | no | wechat manual import path |
| filesystem raw store | crawler storage | implemented | `file_system_store.py` | yes | local knowledge loop |
| filesystem normalized store | crawler storage | implemented | `file_system_store.py` | yes | local knowledge loop |
| sqlite local knowledge index | retrieval | implemented | `sqlite_index_store.py` | yes | retrieval service |
| retrieval search hits | retrieval | implemented | `retrieval/schemas.py` | derived | 2 agents / scripts / tests |
| eligibility local grounding | runtime | partial | feature flag | derived | `eligibility-checker` |
| recommendation local grounding | runtime | partial | feature flag | derived | `competition-recommender` |

## 3. 全类别覆盖现状

| 类别 | 覆盖状态 | 进入本地知识方式 |
| --- | --- | --- |
| 国家政策 | implemented | static HTTP |
| 法律法规 | implemented | static HTTP |
| 社会热点 | importer | JSON importer |
| 就业招聘 | implemented | static HTTP |
| 基金指南 | implemented | static HTTP |
| 获批项目 | implemented | static HTTP |
| 竞赛信息 | implemented | static HTTP + `competitions.json` |
| 获奖作品 | importer | CSV importer |
| 优秀模板 | importer | Markdown importer |
| 经验分享 | importer | TXT importer + WeChat article importer |

## 4. 仍为边界的能力

| Object | Layer | Status | Notes |
| --- | --- | --- | --- |
| placeholder crawler service path | crawler | placeholder | 旧 scaffold 仍保留兼容边界 |
| real multi-site crawler platform | crawler | unimplemented | 无调度、无深分页、无浏览器抓取 |
| attachment binary content | storage | unimplemented | 只存在元数据 |
| runtime database records | storage | unimplemented | 主任务流未接 MySQL / PostgreSQL |

## 5. 当前 source-of-truth 总结

- API 和 runtime 契约：backend Pydantic
- 本地知识 taxonomy 与 source manifest：crawler code + docs mirror
- 本地知识正文：`backend/data/local_knowledge/raw/` 和 `normalized/`
- 本地检索：`backend/data/local_knowledge/knowledge_index.sqlite3`
- 智能体读取入口：retrieval service，而不是 raw crawler 文件
