from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.crawler.taxonomy import DocumentSourceType, SourceChannelType, SourceImplementationStatus


class RetrievalBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class DocumentSearchFilters(RetrievalBaseModel):
    source_type: DocumentSourceType | None = None
    source_types: list[DocumentSourceType] = Field(default_factory=list)
    source_channel: SourceChannelType | None = None
    source_channels: list[SourceChannelType] = Field(default_factory=list)
    source_name: str | None = None
    implementation_status: SourceImplementationStatus | None = None
    implementation_statuses: list[SourceImplementationStatus] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("source_name", mode="before")
    @classmethod
    def _normalize_source_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return _dedupe_strings(value)

    @field_validator("source_types", "source_channels", "implementation_statuses", mode="before")
    @classmethod
    def _normalize_list_filters(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return _dedupe_strings(value)


class DocumentSearchHit(RetrievalBaseModel):
    record_id: str
    doc_id: str
    title: str
    summary: str = ""
    source_type: DocumentSourceType
    source_channel: SourceChannelType
    source_name: str
    implementation_status: SourceImplementationStatus
    tags: list[str] = Field(default_factory=list)
    publish_time: datetime | None = None
    url: str
    score: float | None = None


def _dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for item in values:
        normalized = str(item).strip()
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped
