---
name: competition-domain-context
description: Keep the current competition data model, API shape, and related documentation aligned in CompAssistant. Use when Codex needs to inspect or document `backend/data/competitions.json`, backend schemas, or current frontend expectations before broader changes.
---

# Competition Domain Context

1. Read `backend/data/competitions.json` and `backend/app/schemas/competition.py` first.
2. Treat the JSON file as the current source of truth for competition records.
3. Document mismatches before proposing structural changes.
4. Avoid inventing a database-backed domain model unless the user explicitly asks for migration work.
5. Keep frontend and backend field naming aligned in docs and schemas.
