from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from typing import Any

from ..schemas import KnowledgeRecord, NormalizedDocument, RawDocument


class NormalizePipeline:
    name = "normalize_pipeline"

    def run(self, raw_document: RawDocument) -> NormalizedDocument:
        extracted = _extract_content(raw_document)
        content_text = _normalize_whitespace(extracted["content_text"])
        title = _normalize_title(extracted["title"], raw_document)
        tags = _build_tags(raw_document, extracted.get("tags"))
        checksum = sha256(content_text.encode("utf-8")).hexdigest()
        language = _detect_language(content_text)

        return NormalizedDocument(
            doc_id=raw_document.doc_id,
            source_type=raw_document.source_type,
            source_name=raw_document.source_name,
            url=raw_document.url,
            title=title,
            publish_time=_coerce_datetime(extracted.get("publish_time") or raw_document.metadata.get("publish_time")),
            content_text=content_text,
            tags=tags,
            region=_first_non_empty(
                extracted.get("region"),
                raw_document.metadata.get("region"),
            ),
            school_or_org=_first_non_empty(
                extracted.get("school_or_org"),
                raw_document.metadata.get("school_or_org"),
                raw_document.metadata.get("organization"),
            ),
            raw_ref=raw_document.raw_ref or raw_document.metadata.get("raw_ref") or raw_document.doc_id,
            checksum=checksum,
            language=language,
            collected_at=datetime.now(timezone.utc),
            normalized_metadata={
                "raw_content_type": raw_document.raw_content_type,
                "fetch_method": raw_document.fetch_method,
                "source_metadata": raw_document.metadata,
                "extracted_title": extracted["title"],
            },
        )

    def build_knowledge_record(self, normalized_document: NormalizedDocument) -> KnowledgeRecord:
        summary = _build_summary(normalized_document.content_text)
        searchable_parts = [
            normalized_document.title,
            summary,
            normalized_document.content_text,
            " ".join(normalized_document.tags),
        ]
        searchable_text = "\n".join(part for part in searchable_parts if part).strip()
        return KnowledgeRecord(
            record_id=f"knowledge-{normalized_document.doc_id}",
            doc_id=normalized_document.doc_id,
            title=normalized_document.title,
            summary=summary,
            content_text=normalized_document.content_text,
            source_type=normalized_document.source_type,
            source_name=normalized_document.source_name,
            tags=list(normalized_document.tags),
            publish_time=normalized_document.publish_time,
            url=normalized_document.url,
            searchable_text=searchable_text,
            indexed_at=datetime.now(timezone.utc),
        )


def _extract_content(raw_document: RawDocument) -> dict[str, Any]:
    raw_text = raw_document.raw_text or ""
    if "html" in raw_document.raw_content_type:
        parser = _HTMLContentParser()
        parser.feed(raw_text)
        return {
            "title": parser.title or raw_document.metadata.get("title"),
            "content_text": parser.text_content or raw_document.metadata.get("summary") or raw_document.url,
            "tags": raw_document.metadata.get("tags", []),
            "publish_time": raw_document.metadata.get("publish_time"),
            "region": raw_document.metadata.get("region"),
            "school_or_org": raw_document.metadata.get("school_or_org"),
        }

    if "json" in raw_document.raw_content_type:
        payload = json.loads(raw_text)
        if isinstance(payload, dict):
            suggestions = payload.get("suggestions") or []
            links = payload.get("links") or []
            content_parts = [
                payload.get("description"),
                payload.get("summary"),
                payload.get("content"),
                " ".join(str(item) for item in suggestions),
                " ".join(str(item.get("name")) for item in links if isinstance(item, dict)),
            ]
            tags = [
                str(value)
                for value in (
                    payload.get("field"),
                    payload.get("difficulty"),
                    payload.get("level"),
                    *(payload.get("tags") or []),
                )
                if str(value).strip()
            ]
            return {
                "title": payload.get("title") or payload.get("name"),
                "content_text": _normalize_whitespace(" ".join(str(part) for part in content_parts if part)),
                "tags": tags,
                "publish_time": payload.get("publish_time"),
                "region": payload.get("region"),
                "school_or_org": payload.get("school_or_org"),
            }

    return {
        "title": raw_document.metadata.get("title") or raw_document.url,
        "content_text": _normalize_whitespace(raw_text),
        "tags": raw_document.metadata.get("tags", []),
        "publish_time": raw_document.metadata.get("publish_time"),
        "region": raw_document.metadata.get("region"),
        "school_or_org": raw_document.metadata.get("school_or_org"),
    }


def _normalize_title(raw_title: str | None, raw_document: RawDocument) -> str:
    if raw_title and str(raw_title).strip():
        return _normalize_whitespace(str(raw_title))
    if title := raw_document.metadata.get("title"):
        return _normalize_whitespace(str(title))
    return raw_document.url


def _build_tags(raw_document: RawDocument, extracted_tags: list[str] | None) -> list[str]:
    tags: list[str] = [raw_document.source_type, raw_document.source_name]
    for item in extracted_tags or []:
        normalized = _normalize_whitespace(str(item))
        if normalized and normalized not in tags:
            tags.append(normalized)
    return tags


def _build_summary(content_text: str, limit: int = 240) -> str:
    normalized = _normalize_whitespace(content_text)
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _normalize_whitespace(value: str | None) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip()
    return normalized


def _coerce_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _first_non_empty(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        normalized = str(value).strip()
        if normalized:
            return normalized
    return None


def _detect_language(content_text: str) -> str:
    if any("\u4e00" <= char <= "\u9fff" for char in content_text):
        return "zh-CN"
    return "en"


class _HTMLContentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self._text_chunks: list[str] = []
        self._title_chunks: list[str] = []

    @property
    def title(self) -> str:
        return _normalize_whitespace(" ".join(self._title_chunks))

    @property
    def text_content(self) -> str:
        return _normalize_whitespace(" ".join(self._text_chunks))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        elif normalized_tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1
        elif normalized_tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        normalized = _normalize_whitespace(unescape(data))
        if not normalized:
            return
        if self._in_title:
            self._title_chunks.append(normalized)
        else:
            self._text_chunks.append(normalized)
