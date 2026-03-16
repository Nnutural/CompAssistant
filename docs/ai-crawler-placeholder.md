# AI Crawler Placeholder

This repository no longer has a crawler scaffold that is purely empty. It now has a minimal experimental local knowledge loop.

## What is implemented now

- strict document schemas:
  `RawDocument`, `NormalizedDocument`, `KnowledgeRecord`
- one public static HTTP provider
- one normalization pipeline
- filesystem persistence for raw and normalized documents
- SQLite local index with FTS5 when available
- retrieval service used by one feature-flagged agent path

## What is still intentionally not implemented

- browser automation
- login flows
- CAPTCHA or anti-bot bypass
- multi-site orchestration
- scheduling
- proxy rotation
- generic crawler platform abstractions
- runtime-wide crawler integration
- frontend crawler UI

## Current integration boundary

- The crawler path is still experimental.
- It is not wired into the public API surface.
- It does not change the main runtime flow.
- Only the `eligibility-checker` gets optional local knowledge grounding, and only through retrieval results.

## Storage boundary

- raw and normalized documents go to the local filesystem
- searchable knowledge goes to SQLite
- agents do not read raw crawler files directly

## Future direction

If crawler work expands later, keep the rollout order narrow:

1. one source
2. one validation path
3. one retrieval consumer

Only after that should the project consider a broader crawler platform.
