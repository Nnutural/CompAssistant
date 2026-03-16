from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.crawler.schemas import DocumentSourceType


class RetrievalBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class DocumentSearchFilters(RetrievalBaseModel):
    source_type: DocumentSourceType | None = None
    source_name: str | None = None
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
        deduped: list[str] = []
        for item in value:
            normalized = str(item).strip()
            if normalized and normalized not in deduped:
                deduped.append(normalized)
        return deduped


class DocumentSearchHit(RetrievalBaseModel):
    record_id: str
    doc_id: str
    title: str
    summary: str = ""
    source_type: DocumentSourceType
    source_name: str
    tags: list[str] = Field(default_factory=list)
    publish_time: datetime | None = None
    url: str
    score: float | None = None
