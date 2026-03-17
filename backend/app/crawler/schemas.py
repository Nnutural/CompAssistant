from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .taxonomy import DocumentSourceType, SourceChannelType, SourceImplementationStatus


class CrawlerBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _dedupe_tags(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for item in values:
        normalized = item.strip()
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped


class CrawlRequest(CrawlerBaseModel):
    request_id: str
    source: str
    target: str
    entrypoint: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrawlDocument(CrawlerBaseModel):
    document_id: str
    source: str
    title: str | None = None
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrawlResult(CrawlerBaseModel):
    request_id: str
    provider: str
    status: Literal["placeholder", "not_implemented", "succeeded", "failed"]
    documents: list[CrawlDocument] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RawDocument(CrawlerBaseModel):
    doc_id: str = Field(min_length=1)
    source_type: DocumentSourceType
    source_channel: SourceChannelType
    source_name: str = Field(min_length=1)
    implementation_status: SourceImplementationStatus
    url: str = Field(min_length=1)
    fetch_method: str = Field(min_length=1)
    raw_content_type: str = Field(min_length=1)
    raw_text: str | None = None
    raw_ref: str | None = None
    fetched_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("doc_id", "source_name", "url", "fetch_method", "raw_content_type", mode="before")
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("raw_text", "raw_ref", mode="before")
    @classmethod
    def _normalize_text_refs(cls, value: str | None) -> str | None:
        return _normalize_optional_string(value)

    @model_validator(mode="after")
    def _ensure_raw_payload(self) -> "RawDocument":
        if not self.raw_text and not self.raw_ref:
            raise ValueError("RawDocument requires either raw_text or raw_ref")
        return self


class NormalizedDocument(CrawlerBaseModel):
    doc_id: str = Field(min_length=1)
    source_type: DocumentSourceType
    source_channel: SourceChannelType
    source_name: str = Field(min_length=1)
    implementation_status: SourceImplementationStatus
    url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    publish_time: datetime | None = None
    content_text: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    region: str | None = None
    school_or_org: str | None = None
    raw_ref: str = Field(min_length=1)
    checksum: str = Field(min_length=64, max_length=64)
    language: str = Field(min_length=2)
    collected_at: datetime
    normalized_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("doc_id", "source_name", "url", "title", "content_text", "raw_ref", "checksum", "language", mode="before")
    @classmethod
    def _validate_normalized_strings(cls, value: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("region", "school_or_org", mode="before")
    @classmethod
    def _normalize_optional_fields(cls, value: str | None) -> str | None:
        return _normalize_optional_string(value)

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return _dedupe_tags([str(item) for item in value])


class KnowledgeRecord(CrawlerBaseModel):
    record_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = ""
    content_text: str = Field(min_length=1)
    source_type: DocumentSourceType
    source_channel: SourceChannelType
    source_name: str = Field(min_length=1)
    implementation_status: SourceImplementationStatus
    tags: list[str] = Field(default_factory=list)
    publish_time: datetime | None = None
    url: str = Field(min_length=1)
    searchable_text: str = Field(min_length=1)
    indexed_at: datetime

    @field_validator("record_id", "doc_id", "title", "content_text", "source_name", "url", "searchable_text", mode="before")
    @classmethod
    def _validate_knowledge_strings(cls, value: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("summary", mode="before")
    @classmethod
    def _normalize_summary(cls, value: str | None) -> str:
        return str(value or "").strip()

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_knowledge_tags(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return _dedupe_tags([str(item) for item in value])
