from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.research_runtime import TaskType


class EvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvaluationCase(EvaluationModel):
    id: str
    task_type: TaskType
    input: Dict[str, Any]
    expected_required_fields: List[str] = Field(default_factory=list)
    scoring_rubric: Dict[str, Any] = Field(default_factory=dict)
    optional_notes: Optional[str] = None


class EvaluationCaseResult(EvaluationModel):
    id: str
    task_type: TaskType
    run_id: str
    passed: bool
    status: str
    current_state: Optional[str] = None
    missing_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    result_summary: Optional[str] = None
    quality_score: float = 0.0
    quality_threshold: float = 0.0
    failed_quality_checks: List[str] = Field(default_factory=list)


class EvaluationQualitySummary(EvaluationModel):
    average_score: float
    lowest_score: float
    highest_score: float


class EvaluationSummary(EvaluationModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    warning_cases: int
    low_quality_cases: int
    quality: EvaluationQualitySummary


class EvaluationReport(EvaluationModel):
    summary: EvaluationSummary
    results: List[EvaluationCaseResult] = Field(default_factory=list)
