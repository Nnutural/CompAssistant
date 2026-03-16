# Data Engineering Rules

This repository still prioritizes the existing competition assistant runtime. The experimental local knowledge loop must stay narrow and isolated.

## 1. Source-of-truth rules

- Backend Pydantic models remain the source of truth for API and runtime contracts.
- Local competition JSON datasets remain the source of truth for the existing competition tools.
- Experimental crawler output is not a source of truth until it has been normalized into `NormalizedDocument` and indexed as `KnowledgeRecord`.
- Agents must consume local knowledge through retrieval results only.

## 2. Scope rules for the local knowledge loop

- Allowed in this phase:
  public static HTTP fetches, local file storage, normalization, SQLite FTS5 indexing, retrieval service reads, one feature-flagged agent integration.
- Explicitly out of scope:
  Playwright, login, dynamic rendering, scheduler orchestration, queues, Redis, Celery, vector DB, RAG, WebSocket, MySQL or PostgreSQL migrations.

## 3. Storage rules

- Raw documents are written to the local filesystem.
- Normalized documents are written to the local filesystem.
- Search index uses SQLite.
- FTS5 is the preferred path.
- If FTS5 is unavailable, the code may fall back to a minimal LIKE-based path and must record that compatibility note.

## 4. Normalization rules

- `RawDocument` must contain either inline raw text or a stored raw reference.
- `NormalizedDocument` must contain cleaned text, a stable title, checksum, language, and raw reference.
- `KnowledgeRecord.searchable_text` must be built from title, summary, content, and tags.
- Keep fields minimal. Do not introduce future schema branches that are not consumed yet.

## 5. Runtime integration rules

- Do not introduce new task types.
- Do not refactor the research runtime manager or task flow.
- Do not change competitions API contracts.
- Do not change the main frontend flow.
- Any local knowledge usage inside agents must be guarded by a feature flag.

## 6. Testing rules

New local knowledge changes must keep the following tests in sync:

- schema construction and validation
- normalize pipeline behavior
- sqlite index upsert and search
- retrieval service read path
- one minimal end-to-end local ingestion test
- one minimal agent grounding test if an agent is connected

## 7. Documentation rules

When the local knowledge path changes, update all of the following together:

- `docs/data-inventory.md`
- `docs/data-sources.md`
- `docs/data-contracts.md`
- `docs/data-engineering-rules.md`
- `docs/current-state.md`
- `docs/ai-crawler-placeholder.md`
- `docs/data-manifest.json`
