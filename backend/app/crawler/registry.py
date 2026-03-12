from __future__ import annotations

from .interfaces import CrawlerProvider
from .providers.placeholder_provider import PlaceholderCrawlerProvider


DEFAULT_PROVIDER = "placeholder"

_PROVIDERS: dict[str, CrawlerProvider] = {
    DEFAULT_PROVIDER: PlaceholderCrawlerProvider(),
}


def list_providers() -> list[str]:
    return sorted(_PROVIDERS)


def get_provider(name: str = DEFAULT_PROVIDER) -> CrawlerProvider:
    try:
        return _PROVIDERS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown crawler provider: {name}") from exc
