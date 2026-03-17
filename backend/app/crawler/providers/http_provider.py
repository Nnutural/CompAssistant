from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
from urllib.request import Request, urlopen

from .base import BaseCrawlerProvider
from ..schemas import CrawlDocument, CrawlRequest, CrawlResult, RawDocument


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


class HttpCrawlerProvider(BaseCrawlerProvider):
    name = "http"

    def __init__(self, *, timeout_seconds: float = 15.0, user_agent: str = DEFAULT_USER_AGENT) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def fetch_document(
        self,
        *,
        source_type: str,
        source_channel: str = "public_web",
        source_name: str,
        implementation_status: str = "implemented",
        url: str,
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> RawDocument:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            body = response.read()
            raw_content_type = response.headers.get_content_type() or "text/plain"
            content_type_header = response.headers.get("Content-Type", raw_content_type)
            raw_text = _decode_body(body, response.headers.get_content_charset())
            fetched_at = datetime.now(timezone.utc)
            response_metadata = {
                "content_length": len(body),
                "content_type_header": content_type_header,
                "http_status": getattr(response, "status", None),
                **(metadata or {}),
            }
        return RawDocument(
            doc_id=doc_id or _build_doc_id(source_name, url),
            source_type=source_type,
            source_channel=source_channel,
            source_name=source_name,
            implementation_status=implementation_status,
            url=url,
            fetch_method="http_get",
            raw_content_type=raw_content_type,
            raw_text=raw_text,
            fetched_at=fetched_at,
            metadata=response_metadata,
        )

    def execute(self, request: CrawlRequest) -> CrawlResult:
        raw_document = self.fetch_document(
            source_type=str(request.metadata.get("source_type") or "national_policy"),
            source_channel=str(request.metadata.get("source_channel") or "public_web"),
            source_name=request.source,
            implementation_status=str(request.metadata.get("implementation_status") or "implemented"),
            url=request.entrypoint,
            metadata={"target": request.target, **request.metadata},
        )
        return CrawlResult(
            request_id=request.request_id,
            provider=self.name,
            status="succeeded",
            documents=[
                CrawlDocument(
                    document_id=raw_document.doc_id,
                    source=raw_document.source_name,
                    title=str(raw_document.metadata.get("title") or ""),
                    content=raw_document.raw_text or "",
                    metadata={"url": raw_document.url, "source_type": raw_document.source_type},
                )
            ],
            notes=["HTTP provider fetched a static public document."],
        )


def _build_doc_id(source_name: str, url: str) -> str:
    digest = sha256(f"{source_name}|{url}".encode("utf-8")).hexdigest()[:16]
    normalized_source = "".join(char if char.isalnum() else "-" for char in source_name.lower()).strip("-") or "doc"
    return f"{normalized_source}-{digest}"


def _decode_body(body: bytes, charset: str | None) -> str:
    candidates = [charset, "utf-8", "gb18030", "latin-1"]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return body.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")
