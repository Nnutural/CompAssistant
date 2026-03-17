from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from ..schemas import NormalizedDocument, RawDocument


class FileSystemDocumentStore:
    name = "file_system_store"

    def __init__(self, root_dir: str | Path | None = None) -> None:
        self.root_dir = Path(root_dir) if root_dir else Path(__file__).resolve().parents[3] / "data" / "local_knowledge"
        self.raw_dir = self.root_dir / "raw"
        self.normalized_dir = self.root_dir / "normalized"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.normalized_dir.mkdir(parents=True, exist_ok=True)

    def save_raw(self, document: RawDocument) -> RawDocument:
        path = self.raw_dir / f"{document.doc_id}.json"
        payload = document.model_dump(mode="json")
        payload["raw_ref"] = self._relative_path(path)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return document.model_copy(update={"raw_ref": payload["raw_ref"]})

    def save_normalized(self, document: NormalizedDocument) -> NormalizedDocument:
        path = self.normalized_dir / f"{document.doc_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(document.model_dump(mode="json"), handle, ensure_ascii=False, indent=2)
        return document

    def iter_normalized_documents(self) -> list[NormalizedDocument]:
        documents: list[NormalizedDocument] = []
        for path in sorted(self.normalized_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                try:
                    documents.append(NormalizedDocument.model_validate(json.load(handle)))
                except ValidationError:
                    continue
        return documents

    def _relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.root_dir.resolve()).as_posix()
