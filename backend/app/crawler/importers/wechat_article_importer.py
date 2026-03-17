from __future__ import annotations

from pathlib import Path
from typing import Any

from ..schemas import RawDocument
from .file_importer import FileDocumentImporter
from .structured_importer import StructuredDataImporter


class WeChatArticleImporter:
    name = "wechat_article_importer"

    def __init__(
        self,
        *,
        file_importer: FileDocumentImporter | None = None,
        structured_importer: StructuredDataImporter | None = None,
    ) -> None:
        self.file_importer = file_importer or FileDocumentImporter()
        self.structured_importer = structured_importer or StructuredDataImporter()

    def import_article(
        self,
        path: str | Path,
        *,
        source_type: str,
        source_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[RawDocument]:
        file_path = Path(path)
        if file_path.suffix.lower() in {".json", ".csv"}:
            return self.structured_importer.import_file(
                file_path,
                source_type=source_type,
                source_name=source_name,
                source_channel="wechat_official_account",
                implementation_status="importer",
                metadata=metadata,
            )
        return self.file_importer.import_file(
            file_path,
            source_type=source_type,
            source_name=source_name,
            source_channel="wechat_official_account",
            implementation_status="importer",
            metadata=metadata,
        )
