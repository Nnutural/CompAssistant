from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PlaceholderSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = "placeholder"
    label: str = "Placeholder Source"
    description: str = "A non-functional source definition reserved for future crawler adapters."
    capabilities: list[str] = Field(default_factory=lambda: ["placeholder"])
