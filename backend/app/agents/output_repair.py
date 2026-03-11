from __future__ import annotations

import json
import re
from typing import Any, Literal, get_args, get_origin

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


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
    if len(payload) == 1:
        only_key, only_value = next(iter(payload.items()))
        if isinstance(only_value, dict) and str(only_key).endswith("_artifact"):
            warnings.append(f"Unwrapped payload from '{only_key}'.")
            return only_value
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
    _apply_model_aliases(normalized, output_model, warnings, field_name="root")
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
        _apply_model_aliases(normalized, annotation, warnings, field_name=field_name)
        return normalized
    if origin is Literal and isinstance(value, str):
        return _coerce_literal(value, args, warnings, field_name)
    if origin is list and isinstance(value, str):
        warnings.append(f"Split string value into list for '{field_name}'.")
        items = [item.strip(" -") for item in re.split(r"[\n,]+", value) if item.strip()]
        return items
    if origin is list and isinstance(value, dict):
        warnings.append(f"Flattened object value into list for '{field_name}'.")
        return [f"{key}: {str(item).strip()}" for key, item in value.items() if str(item).strip()]
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


def _coerce_literal(value: str, allowed_values: tuple[Any, ...], warnings: list[str], field_name: str) -> Any:
    normalized_value = value.strip()
    lowered = normalized_value.lower()
    allowed_map = {str(item): item for item in allowed_values}
    allowed_lower_map = {str(item).lower(): item for item in allowed_values}
    aliases = {
        "algorithm_competition_recommendation": "competition_recommendation",
        "algorithm_programming_competition_recommendation": "competition_recommendation",
        "competition_recommend": "competition_recommendation",
        "recommendation": "competition_recommendation",
        "competition_recommendation_artifact": "competition_recommendation",
        "eligibility": "competition_eligibility_check",
        "eligibility_check": "competition_eligibility_check",
        "competition_eligibility": "competition_eligibility_check",
        "competition_eligibility_artifact": "competition_eligibility_check",
        "timeline": "competition_timeline_plan",
        "timeline_plan": "competition_timeline_plan",
        "competition_timeline": "competition_timeline_plan",
        "competition_timeline_artifact": "competition_timeline_plan",
    }
    if normalized_value in allowed_map:
        return allowed_map[normalized_value]
    if lowered in allowed_lower_map:
        warnings.append(f"Normalized literal casing for '{field_name}'.")
        return allowed_lower_map[lowered]
    alias_target = aliases.get(lowered)
    if alias_target and alias_target in allowed_map:
        warnings.append(f"Mapped literal alias for '{field_name}' from '{value}' to '{alias_target}'.")
        return allowed_map[alias_target]
    if "recommend" in lowered and "competition_recommendation" in allowed_map:
        warnings.append(f"Mapped fuzzy recommendation literal for '{field_name}' from '{value}'.")
        return allowed_map["competition_recommendation"]
    if "eligibility" in lowered and "competition_eligibility_check" in allowed_map:
        warnings.append(f"Mapped fuzzy eligibility literal for '{field_name}' from '{value}'.")
        return allowed_map["competition_eligibility_check"]
    if "timeline" in lowered and "competition_timeline_plan" in allowed_map:
        warnings.append(f"Mapped fuzzy timeline literal for '{field_name}' from '{value}'.")
        return allowed_map["competition_timeline_plan"]
    return value


def _apply_model_aliases(
    payload: dict[str, Any],
    model_type: type[BaseModel],
    warnings: list[str],
    *,
    field_name: str,
) -> None:
    if "task_type" in model_type.model_fields and "task_type" not in payload:
        task_type_defaults = _extract_literal_defaults(model_type.model_fields["task_type"].annotation)
        if len(task_type_defaults) == 1:
            payload["task_type"] = task_type_defaults[0]
            warnings.append(f"Filled missing task_type for '{field_name}' with '{task_type_defaults[0]}'.")
    if "profile_summary" in model_type.model_fields and "profile_summary" not in payload:
        payload["profile_summary"] = "Profile summary inferred from provider output."
        warnings.append(f"Filled missing profile_summary for '{field_name}'.")
    if "risk_overview" in model_type.model_fields and "risk_overview" not in payload:
        recommendations = payload.get("recommendations")
        if isinstance(recommendations, list):
            aggregated_risks: list[str] = []
            for item in recommendations:
                if not isinstance(item, dict):
                    continue
                risk_notes = item.get("risk_notes")
                if isinstance(risk_notes, str):
                    aggregated_risks.extend(
                        note.strip(" -") for note in re.split(r"[\n,]+", risk_notes) if note.strip()
                    )
                elif isinstance(risk_notes, list):
                    aggregated_risks.extend(str(note).strip() for note in risk_notes if str(note).strip())
            if aggregated_risks:
                payload["risk_overview"] = list(dict.fromkeys(aggregated_risks))[:6]
                warnings.append(f"Filled missing risk_overview for '{field_name}' from recommendation risk notes.")
    if "competition_id" in model_type.model_fields and "competition_id" not in payload and payload.get("id") is not None:
        payload["competition_id"] = payload.get("id")
        warnings.append(f"Mapped id to competition_id for '{field_name}'.")
    if "competition_name" in model_type.model_fields and "competition_name" not in payload and payload.get("name"):
        payload["competition_name"] = payload.get("name")
        warnings.append(f"Mapped name to competition_name for '{field_name}'.")
    if "competition" in payload and isinstance(payload["competition"], dict):
        competition = payload["competition"]
        if "competition_id" in model_type.model_fields and "competition_id" not in payload and competition.get("id") is not None:
            payload["competition_id"] = competition.get("id")
            warnings.append(f"Recovered competition_id from nested competition for '{field_name}'.")
        if "competition_name" in model_type.model_fields and "competition_name" not in payload and competition.get("name"):
            payload["competition_name"] = competition.get("name")
            warnings.append(f"Recovered competition_name from nested competition for '{field_name}'.")
        if "competition" not in model_type.model_fields:
            payload.pop("competition", None)
            warnings.append(f"Removed nested competition wrapper for '{field_name}'.")
    if "competition_id" in model_type.model_fields and "competition_id" not in payload and payload.get("competition_name"):
        resolved_competition_id = _resolve_competition_id_by_name(str(payload["competition_name"]))
        if resolved_competition_id is not None:
            payload["competition_id"] = resolved_competition_id
            warnings.append(
                f"Resolved competition_id from competition_name for '{field_name}' via local competitions dataset."
            )
    if "match_score" in model_type.model_fields and "match_score" not in payload and payload.get("score") is not None:
        payload["match_score"] = payload.get("score")
        warnings.append(f"Mapped score to match_score for '{field_name}'.")
    if "score" in payload and "score" not in model_type.model_fields:
        payload.pop("score", None)
        warnings.append(f"Removed score alias field for '{field_name}'.")
    if "id" in payload and "id" not in model_type.model_fields:
        payload.pop("id", None)
        warnings.append(f"Removed id alias field for '{field_name}'.")
    if "name" in payload and "name" not in model_type.model_fields:
        payload.pop("name", None)
        warnings.append(f"Removed name alias field for '{field_name}'.")
    allowed_fields = set(model_type.model_fields)
    extra_keys = [key for key in payload if key not in allowed_fields]
    for key in extra_keys:
        payload.pop(key, None)
        warnings.append(f"Removed unexpected field '{key}' for '{field_name}'.")


def _extract_literal_defaults(annotation: Any) -> tuple[Any, ...]:
    origin = get_origin(annotation)
    if origin is Literal:
        return get_args(annotation)
    return ()


@lru_cache(maxsize=1)
def _competition_name_to_id_map() -> dict[str, int]:
    path = DATA_DIR / "competitions.json"
    with path.open("r", encoding="utf-8") as handle:
        competitions = json.load(handle)
    mapping: dict[str, int] = {}
    for item in competitions:
        try:
            competition_id = int(item["id"])
        except (KeyError, TypeError, ValueError):
            continue
        name = str(item.get("name", "")).strip()
        if name:
            mapping[name] = competition_id
            mapping[name.casefold()] = competition_id
    return mapping


def _resolve_competition_id_by_name(raw_name: str) -> int | None:
    name = raw_name.strip()
    if not name:
        return None
    mapping = _competition_name_to_id_map()
    return mapping.get(name) or mapping.get(name.casefold())
