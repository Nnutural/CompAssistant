from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..schemas import RawDocument


class FileDocumentImporter:
    name = "file_importer"

    def import_file(
        self,
        path: str | Path,
        *,
        source_type: str,
        source_name: str,
        source_channel: str = "local_file",
        implementation_status: str = "importer",
        url: str | None = None,
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> list[RawDocument]:
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        if suffix not in {".md", ".txt", ".html", ".htm"}:
            raise ValueError(f"Unsupported file importer suffix: {suffix}")

        raw_text = file_path.read_text(encoding="utf-8")
        effective_url = url or f"local://{file_path.name}"
        effective_doc_id = doc_id or _build_doc_id(source_name, file_path)
        raw_content_type = _resolve_content_type(suffix)
        payload_metadata = {
            "source_path": str(file_path),
            **(metadata or {}),
        }

        return [
            RawDocument(
                doc_id=effective_doc_id,
                source_type=source_type,
                source_channel=source_channel,
                source_name=source_name,
                implementation_status=implementation_status,
                url=effective_url,
                fetch_method="manual_file_import",
                raw_content_type=raw_content_type,
                raw_text=raw_text,
                fetched_at=datetime.now(timezone.utc),
                metadata=payload_metadata,
            )
        ]


def _build_doc_id(source_name: str, path: Path) -> str:
    digest = sha256(f"{source_name}|{path.resolve()}".encode("utf-8")).hexdigest()[:12]
    normalized_stem = "".join(char if char.isalnum() else "-" for char in path.stem.lower()).strip("-") or "doc"
    return f"{normalized_stem}-{digest}"


def _resolve_content_type(suffix: str) -> str:
    if suffix == ".md":
        return "text/markdown"
    if suffix in {".html", ".htm"}:
        return "text/html"
    return "text/plain"
