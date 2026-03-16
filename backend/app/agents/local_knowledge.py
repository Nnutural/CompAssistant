from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.retrieval import DocumentSearchHit, search_documents
from app.tools import load_competition_by_id, unwrap_tool_result


def find_local_knowledge_for_competition(
    competition_id: int,
    profile: dict[str, Any],
    *,
    top_k: int | None = None,
) -> list[DocumentSearchHit]:
    if not settings.experimental_local_knowledge_enabled:
        return []

    competition = unwrap_tool_result(load_competition_by_id(competition_id), "load_competition_by_id")
    direction = str(profile.get("direction") or profile.get("field") or "").strip()
    query_parts = [
        str(competition.get("name") or "").strip(),
        str(competition.get("field") or "").strip(),
        direction,
        "eligibility rules competition policy",
    ]
    query = " ".join(part for part in query_parts if part)
    if not query:
        return []
    limit = top_k or settings.experimental_local_knowledge_top_k
    return search_documents(query, top_k=max(1, int(limit)))
