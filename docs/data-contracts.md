# Data Contracts

This document tracks the stable contracts that the repository currently relies on.

## Contract baseline

- Backend Pydantic models remain the source of truth for API and runtime contracts.
- Existing task, ledger, artifact, and competition contracts are unchanged in this phase.
- The local knowledge loop is experimental and isolated behind a retrieval service plus a feature flag.
- Agents must not read raw crawler files directly. They can only consume normalized knowledge through retrieval outputs.

## Existing stable contracts

- `backend/app/schemas/agent_tasks.py`
  Current task API request, status, event, artifact, history, and control contracts.
- `backend/app/schemas/research_runtime.py`
  Current runtime ledger and competition artifact contracts.
- `backend/app/schemas/competition.py`
  Current competitions API response contract.

## Experimental local knowledge contracts

Location: `backend/app/crawler/schemas.py`

### `RawDocument`

- `doc_id`: required string
- `source_type`: required enum, currently `policy | competition`
- `source_name`: required string
- `url`: required string
- `fetch_method`: required string
- `raw_content_type`: required string
- `raw_text`: optional string
- `raw_ref`: optional string
- `fetched_at`: required datetime
- `metadata`: required object, default `{}`

Validation notes:

- Extra fields are forbidden.
- At least one of `raw_text` or `raw_ref` is required.

### `NormalizedDocument`

- `doc_id`: required string
- `source_type`: required enum, currently `policy | competition`
- `source_name`: required string
- `url`: required string
- `title`: required string
- `publish_time`: optional datetime
- `content_text`: required string
- `tags`: required string array, default `[]`
- `region`: optional string
- `school_or_org`: optional string
- `raw_ref`: required string
- `checksum`: required sha256 hex string
- `language`: required string
- `collected_at`: required datetime
- `normalized_metadata`: required object, default `{}`

Validation notes:

- Extra fields are forbidden.
- Tags are deduplicated.

### `KnowledgeRecord`

- `record_id`: required string
- `doc_id`: required string
- `title`: required string
- `summary`: optional string, default `""`
- `content_text`: required string
- `source_type`: required enum, currently `policy | competition`
- `source_name`: required string
- `tags`: required string array, default `[]`
- `publish_time`: optional datetime
- `url`: required string
- `searchable_text`: required string
- `indexed_at`: required datetime

Validation notes:

- Extra fields are forbidden.
- `searchable_text` is built from title, summary, content, and tags before indexing.

## Retrieval contracts

Location: `backend/app/retrieval/schemas.py`

### `DocumentSearchFilters`

- `source_type`: optional enum
- `source_name`: optional string
- `tags`: optional string array, default `[]`

### `DocumentSearchHit`

- `record_id`
- `doc_id`
- `title`
- `summary`
- `source_type`
- `source_name`
- `tags`
- `publish_time`
- `url`
- `score`

## Boundaries kept in this phase

- No new task types
- No runtime refactor
- No competitions API contract changes
- No frontend contract changes
- No browser automation
- No login or anti-bot handling
- No Redis, Celery, vector database, or RAG stack
