# Current State

## Main product path

The main system remains the competition assistant backend plus the existing task, run, events, artifacts, and competitions APIs.

Stable paths still in place:

- competitions API
- existing competition runtime tools
- mock runtime and Agents SDK runtime
- task history, retry, cancel, and review flows
- current frontend task flow

## Experimental local knowledge path added in this phase

This phase adds a minimal local-only document loop that is intentionally decoupled from the main product path.

Implemented now:

- three-layer schema: `RawDocument`, `NormalizedDocument`, `KnowledgeRecord`
- one real public static `http_provider`
- one `normalize_pipeline`
- local filesystem persistence for raw and normalized documents
- local `sqlite_index_store` with SQLite + FTS5
- retrieval service with `search_documents()` and `get_document()`
- one feature-flagged agent integration:
  `eligibility-checker` can use local retrieval results

Current minimal source set:

- one public static policy page over HTTP
- one competition source from `backend/data/competitions.json`

## Deliberate boundaries that remain unchanged

- no new task types
- no runtime refactor
- no competitions API change
- no frontend main-flow change
- no Playwright
- no login or anti-bot handling
- no Redis, Celery, queues, vector DB, or RAG stack
- no MySQL or PostgreSQL migration

## What is still not implemented

- a real multi-site crawler platform
- browser-based crawling
- source scheduling
- deep pagination
- authenticated sources
- dynamic rendering
- direct raw-web access inside agents
