from __future__ import annotations

import json
import re
from typing import Any, get_args, get_origin

from pydantic import BaseModel, Field


class RepairResult(BaseModel):
    raw_output: Any
    extracted_output: Any | None = None
    repaired_output: Any | None = None
    parse_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def repair_output_to_model(raw_output: Any, output_model: type[BaseModel]) -> RepairResult:
    parse_errors: list[str] = []
    warnings: list[str] = []
    extracted_output = _extract_payload(raw_output, parse_errors, warnings)
    repaired_output = _normalize_payload(extracted_output, output_model, warnings)
    return RepairResult(
        raw_output=raw_output,
        extracted_output=extracted_output,
        repaired_output=repaired_output,
        parse_errors=parse_errors,
        warnings=warnings,
    )


def _extract_payload(raw_output: Any, parse_errors: list[str], warnings: list[str]) -> Any | None:
    if isinstance(raw_output, BaseModel):
        return raw_output.model_dump(mode="json", exclude_none=True)
    if isinstance(raw_output, dict):
        return _unwrap_common_wrappers(raw_output, warnings)
    if isinstance(raw_output, str):
        text = raw_output.strip()
        if not text:
            parse_errors.append("Output text is empty.")
            return None
        fenced_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
        if fenced_match:
            text = fenced_match.group(1).strip()
        for candidate in (text, _slice_json_candidate(text)):
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
                return _unwrap_common_wrappers(parsed, warnings) if isinstance(parsed, dict) else parsed
            except json.JSONDecodeError:
                continue
        parse_errors.append("Unable to extract a JSON object from raw output.")
        return None
    return raw_output


def _slice_json_candidate(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return None


def _unwrap_common_wrappers(payload: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    for key in ("result", "data", "output", "artifact", "final_output"):
        value = payload.get(key)
        if isinstance(value, dict):
            warnings.append(f"Unwrapped payload from '{key}'.")
            return value
    return payload


def _normalize_payload(
    payload: Any | None,
    output_model: type[BaseModel],
    warnings: list[str],
) -> Any | None:
    if not isinstance(payload, dict):
        return payload

    normalized = dict(payload)
    for field_name, field_info in output_model.model_fields.items():
        if field_name not in normalized:
            continue
        normalized[field_name] = _coerce_value(normalized[field_name], field_info.annotation, warnings, field_name)
    return normalized


def _coerce_value(value: Any, annotation: Any, warnings: list[str], field_name: str) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel) and isinstance(value, dict):
        normalized = dict(value)
        for nested_name, nested_field in annotation.model_fields.items():
            if nested_name not in normalized:
                continue
            normalized[nested_name] = _coerce_value(
                normalized[nested_name],
                nested_field.annotation,
                warnings,
                f"{field_name}.{nested_name}",
            )
        return normalized
    if origin is list and isinstance(value, str):
        warnings.append(f"Split string value into list for '{field_name}'.")
        items = [item.strip(" -") for item in re.split(r"[\n,]+", value) if item.strip()]
        return items
    if annotation is bool and isinstance(value, str):
        lowered = value.strip().lower()
        return lowered in {"true", "1", "yes", "recommended"}
    if annotation in (int, float) and isinstance(value, str):
        try:
            return annotation(value)
        except ValueError:
            return value
    if origin is list and args:
        inner = args[0]
        if isinstance(value, list):
            return [_coerce_value(item, inner, warnings, field_name) for item in value]
    return value
