---
name: agent-contract-scaffold
description: Define or update future agent interface contracts for CompAssistant. Use when Codex needs to add or revise schemas, handoff docs, env examples, or placeholder documentation without introducing real runtime integration.
---

# Agent Contract Scaffold

1. Start from `docs/schemas/` and `docs/codex-agent-scaffold.md`.
2. Keep outputs implementation-agnostic and documentation-first.
3. Prefer JSON Schema, README notes, and env examples over executable code.
4. Mark reserved fields and placeholders clearly.
5. Do not add real OpenAI or agent SDK calls.
