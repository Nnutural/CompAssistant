from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_RUNTIME_MODES = ("mock", "agents_sdk")
DEPRECATED_RUNTIME_ALIASES = {"live": "agents_sdk"}


@dataclass(frozen=True)
class RuntimeModeResolution:
    requested_runtime_mode: str
    normalized_runtime_mode: str
    warning: str | None = None


def resolve_runtime_mode(raw_mode: str | None) -> RuntimeModeResolution:
    mode = (raw_mode or "mock").strip().lower()
    if mode in SUPPORTED_RUNTIME_MODES:
        return RuntimeModeResolution(
            requested_runtime_mode=mode,
            normalized_runtime_mode=mode,
        )

    if mode in DEPRECATED_RUNTIME_ALIASES:
        target = DEPRECATED_RUNTIME_ALIASES[mode]
        raise ValueError(
            f"runtime_mode='{mode}' is deprecated and no longer accepted. "
            f"Use '{target}' for the Ark Agents SDK path or 'mock' for the local mock path."
        )

    supported = ", ".join(SUPPORTED_RUNTIME_MODES)
    raise ValueError(f"Unsupported runtime_mode='{raw_mode}'. Supported modes: {supported}.")
