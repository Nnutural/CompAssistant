# Phase 5A Demo

## Goal

Demonstrate the new async task flow and the minimal Agent panel without affecting the existing competitions pages.

## Steps

1. Start the backend.
2. Start the frontend.
3. Open the app and click the `Agent` tab in the sidebar.
4. Leave the default task template or choose another task type.
5. Click `Create task`.
6. Confirm that the UI shows a `run_id` immediately.
7. Watch the run move from `queued` to later states in the status card and event timeline.
8. Wait for the run to reach `completed`, `failed`, or `awaiting_review`.
9. Confirm that artifacts appear after terminal completion.
10. Click back to `Competitions` and confirm the existing page still behaves normally.

## Suggested checks

- create returns immediately instead of waiting for full execution
- event timeline keeps updating while the run is active
- artifacts are empty before terminal completion and visible after it
- `awaiting_review` stops polling and keeps the final warning visible
- the legacy competitions workflow is unchanged

## Useful commands

Backend:

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm run dev
```
