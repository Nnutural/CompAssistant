from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CrawlerBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


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
    status: Literal["placeholder", "not_implemented"]
    documents: list[CrawlDocument] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
