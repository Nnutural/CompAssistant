# Data Inventory

Status labels used here:

- `implemented`: live in code and currently consumable
- `partial`: present but only used by part of the flow
- `placeholder`: scaffold exists but the real platform is not implemented
- `unimplemented`: documented future boundary only

## Core runtime data

| Object | Layer | Status | Source of truth | Persisted | Main consumers |
| --- | --- | --- | --- | --- | --- |
| `AgentTaskCreateRequest` | backend api | implemented | backend Pydantic | no | task API |
| `AgentTaskStatusResponse` | backend api | implemented | backend Pydantic | derived | task API / frontend |
| `ResearchLedger` | runtime | implemented | backend Pydantic | yes | runtime service / history / artifacts |
| competition artifacts | runtime | implemented | backend Pydantic | yes | runtime / evaluation / frontend |
| competitions static datasets | storage | implemented | local JSON files | yes | competitions API / runtime tools |

## Experimental local knowledge data

| Object | Layer | Status | Source of truth | Persisted | Main consumers |
| --- | --- | --- | --- | --- | --- |
| `RawDocument` | crawler | implemented | `backend/app/crawler/schemas.py` | yes | local ingestion service |
| `NormalizedDocument` | crawler | implemented | `backend/app/crawler/schemas.py` | yes | normalize pipeline / local ingestion service |
| `KnowledgeRecord` | retrieval | implemented | `backend/app/crawler/schemas.py` | yes | sqlite index / retrieval service |
| filesystem raw store | crawler storage | implemented | `backend/app/crawler/storage/file_system_store.py` | yes | experimental local loop |
| filesystem normalized store | crawler storage | implemented | `backend/app/crawler/storage/file_system_store.py` | yes | experimental local loop |
| sqlite local knowledge index | retrieval | implemented | `backend/app/retrieval/sqlite_index_store.py` | yes | retrieval service |
| retrieval search hits | retrieval | implemented | `backend/app/retrieval/schemas.py` | derived | search service / eligibility agent |
| eligibility local knowledge path | runtime | partial | feature-flagged service boundary | derived | `eligibility-checker` only |

## Placeholder and future boundaries

| Object | Layer | Status | Notes |
| --- | --- | --- | --- |
| placeholder crawler service path | crawler | placeholder | still exists for compatibility and tests |
| real multi-site crawler platform | crawler | unimplemented | no scheduler, no browser automation, no login |
| runtime database records | storage | unimplemented | MySQL config exists, but active task flow does not use it |
| attachment binary content | storage | unimplemented | only metadata exists today |

## Current source-of-truth summary

- Task and runtime contracts: backend Pydantic models
- Competition catalog and runtime rules: local JSON under `backend/data/`
- Experimental local knowledge documents: normalized JSON + SQLite index under `backend/data/local_knowledge/`
- Search consumers must read `KnowledgeRecord` results through retrieval, not raw crawler files
