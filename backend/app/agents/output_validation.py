from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError


NON_EMPTY_FIELDS: dict[str, list[str]] = {
    "CompetitionRecommendationArtifact": ["recommendations"],
    "CompetitionEligibilityArtifact": ["rationale", "attention_points"],
    "CompetitionTimelineArtifact": ["preparation_checklist", "milestones", "stage_plan"],
}


class OutputValidationResult(BaseModel):
    validated_output: BaseModel | None = None
    validation_errors: list[str] = Field(default_factory=list)
    review_required: bool = False
    review_message: str | None = None


def validate_output_against_model(payload: Any, output_model: type[BaseModel]) -> OutputValidationResult:
    try:
        validated_output = output_model.model_validate(payload)
    except ValidationError as exc:
        return OutputValidationResult(
            validated_output=None,
            validation_errors=[_format_error(item) for item in exc.errors()],
            review_required=True,
            review_message=f"{output_model.__name__} validation failed.",
        )

    review_message = _check_review_requirements(validated_output)
    return OutputValidationResult(
        validated_output=validated_output,
        validation_errors=[],
        review_required=review_message is not None,
        review_message=review_message,
    )


def _check_review_requirements(model: BaseModel) -> str | None:
    required_non_empty = NON_EMPTY_FIELDS.get(model.__class__.__name__, [])
    for field_name in required_non_empty:
        value = getattr(model, field_name, None)
        if isinstance(value, list) and not value:
            return f"Field '{field_name}' is empty and requires review."
        if isinstance(value, str) and not value.strip():
            return f"Field '{field_name}' is blank and requires review."
    return None


def _format_error(item: dict[str, Any]) -> str:
    location = ".".join(str(part) for part in item.get("loc", []))
    return f"{location}: {item.get('msg', 'validation error')}"
