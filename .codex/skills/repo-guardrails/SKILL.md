---
name: repo-guardrails
description: Preserve the CompAssistant repository structure and additive-only change policy. Use when Codex needs to add scaffolding, documentation, placeholder directories, or other non-invasive support files without modifying current runtime behavior.
---

# Repo Guardrails

1. Read `AGENTS.md`, `docs/current-state.md`, and `docs/codex-agent-scaffold.md` before editing.
2. Prefer adding files over editing existing runtime code.
3. Preserve the existing `backend/` and `frontend/` directory layout.
4. Use placeholder zones for agent-related work until the user explicitly requests implementation.
5. Stop before wiring imports, routes, background jobs, SDK clients, or UI flows.
6. Use `GIT_TRACKING.md` when deciding what belongs in version control.
