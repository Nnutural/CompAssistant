from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.retrieval import DocumentSearchHit, search_documents
from app.tools import load_competition_by_id, unwrap_tool_result


def search_local_knowledge(
    query: str,
    *,
    source_types: list[str] | None = None,
    source_channels: list[str] | None = None,
    top_k: int | None = None,
) -> list[DocumentSearchHit]:
    if not settings.experimental_local_knowledge_enabled:
        return []

    normalized_query = str(query or "").strip()
    if not normalized_query:
        return []
    limit = top_k or settings.experimental_local_knowledge_top_k
    filters: dict[str, object] = {}
    if source_types:
        filters["source_types"] = source_types
    if source_channels:
        filters["source_channels"] = source_channels
    return search_documents(normalized_query, filters=filters or None, top_k=max(1, int(limit)))


def find_local_knowledge_for_competition(
    competition_id: int,
    profile: dict[str, Any],
    *,
    top_k: int | None = None,
) -> list[DocumentSearchHit]:
    competition = unwrap_tool_result(load_competition_by_id(competition_id), "load_competition_by_id")
    direction = str(profile.get("direction") or profile.get("field") or "").strip()
    query_parts = [
        str(competition.get("name") or "").strip(),
        str(competition.get("field") or "").strip(),
        direction,
        "eligibility competition policy regulation recruitment",
    ]
    return search_local_knowledge(
        " ".join(part for part in query_parts if part),
        source_types=["national_policy", "law_regulation", "competition_info", "employment_recruitment"],
        top_k=top_k,
    )


def find_local_knowledge_for_recommendation(
    profile: dict[str, Any],
    *,
    top_k: int | None = None,
) -> list[DocumentSearchHit]:
    direction = str(profile.get("direction") or profile.get("field") or "").strip()
    interests = profile.get("interests") or []
    if isinstance(interests, str):
        interests = [interests]
    ability_tags = profile.get("ability_tags") or []
    query_parts = [
        direction,
        " ".join(str(item).strip() for item in interests if str(item).strip()),
        " ".join(str(item).strip() for item in ability_tags if str(item).strip()),
        "competition fund project template experience award",
    ]
    return search_local_knowledge(
        " ".join(part for part in query_parts if part),
        source_types=[
            "competition_info",
            "fund_guide",
            "approved_project",
            "award_winning_work",
            "excellent_template",
            "experience_sharing",
        ],
        top_k=top_k,
    )
