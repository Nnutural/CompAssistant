from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..schemas import RawDocument


class CompetitionCatalogSource:
    source_name = "competition_catalog_static"
    source_type = "competition"

    def __init__(self, data_path: str | Path | None = None) -> None:
        self.data_path = Path(data_path) if data_path else Path(__file__).resolve().parents[3] / "data" / "competitions.json"

    def load_raw_documents(self, *, limit: int | None = 1) -> list[RawDocument]:
        with self.data_path.open("r", encoding="utf-8") as handle:
            competitions = json.load(handle)

        documents: list[RawDocument] = []
        for item in competitions[: limit or len(competitions)]:
            url = _resolve_competition_url(item)
            documents.append(
                RawDocument(
                    doc_id=f"competition-{int(item['id'])}",
                    source_type=self.source_type,
                    source_name=self.source_name,
                    url=url,
                    fetch_method="local_json_extract",
                    raw_content_type="application/json",
                    raw_text=json.dumps(item, ensure_ascii=False),
                    fetched_at=datetime.now(timezone.utc),
                    metadata={
                        "competition_id": item["id"],
                        "field": item.get("field"),
                        "difficulty": item.get("difficulty"),
                        "level": item.get("level"),
                        "source_path": str(self.data_path),
                    },
                )
            )
        return documents


def _resolve_competition_url(item: dict) -> str:
    links = item.get("links") or []
    for link in links:
        if isinstance(link, dict) and str(link.get("url") or "").strip():
            return str(link["url"]).strip()
    return f"internal://competitions/{item['id']}"
