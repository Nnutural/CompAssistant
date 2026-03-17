from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..schemas import RawDocument


class StructuredDataImporter:
    name = "structured_importer"

    def import_file(
        self,
        path: str | Path,
        *,
        source_type: str,
        source_name: str,
        source_channel: str = "manual_import",
        implementation_status: str = "importer",
        metadata: dict[str, Any] | None = None,
    ) -> list[RawDocument]:
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        if suffix == ".json":
            records = self._load_json_records(file_path)
        elif suffix == ".csv":
            records = self._load_csv_records(file_path)
        else:
            raise ValueError(f"Unsupported structured importer suffix: {suffix}")

        documents: list[RawDocument] = []
        for index, item in enumerate(records, start=1):
            normalized = _normalize_record(item)
            documents.append(
                RawDocument(
                    doc_id=str(normalized.get("doc_id") or _build_doc_id(source_name, file_path, index)),
                    source_type=source_type,
                    source_channel=str(normalized.get("source_channel") or source_channel),
                    source_name=str(normalized.get("source_name") or source_name),
                    implementation_status=str(normalized.get("implementation_status") or implementation_status),
                    url=str(normalized.get("url") or f"manual://{source_name}/{file_path.stem}/{index}"),
                    fetch_method="manual_structured_import",
                    raw_content_type="application/json",
                    raw_text=json.dumps(normalized, ensure_ascii=False),
                    fetched_at=datetime.now(timezone.utc),
                    metadata={
                        "source_path": str(file_path),
                        **(metadata or {}),
                    },
                )
            )
        return documents

    def _load_json_records(self, path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            if isinstance(payload.get("items"), list):
                return [item for item in payload["items"] if isinstance(item, dict)]
            return [payload]
        raise ValueError("JSON importer payload must be an object or an array of objects")

    def _load_csv_records(self, path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [dict(row) for row in reader]


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    tags = record.get("tags") or []
    if isinstance(tags, str):
        tags = [item.strip() for item in tags.replace("|", ",").split(",") if item.strip()]
    normalized = dict(record)
    normalized["tags"] = tags if isinstance(tags, list) else []
    return normalized


def _build_doc_id(source_name: str, path: Path, index: int) -> str:
    digest = sha256(f"{source_name}|{path.resolve()}|{index}".encode("utf-8")).hexdigest()[:12]
    normalized_stem = "".join(char if char.isalnum() else "-" for char in path.stem.lower()).strip("-") or "record"
    return f"{normalized_stem}-{index}-{digest}"
