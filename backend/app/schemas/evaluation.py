from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.research_runtime import RuntimeMode, TaskType


CompletionPath = Literal["mock", "provider", "mock_fallback", "awaiting_review", "failed", "cancelled"]


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
    completion_path: CompletionPath
    requested_runtime_mode: Optional[str] = None
    effective_runtime_mode: Optional[RuntimeMode] = None
    effective_model: Optional[str] = None
    used_mock_fallback: bool = False
    fallback_reason: Optional[str] = None
    elapsed_ms: Optional[float] = None
    artifact_complete: bool = False
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


class EvaluationRuntimeSummary(EvaluationModel):
    requested_runtime_mode: str
    direct_success_rate: float
    fallback_rate: float
    hard_failure_rate: float
    awaiting_review_ratio: float
    artifact_completeness_ratio: float
    avg_latency_ms: float
    p95_latency_ms: float


class EvaluationSummary(EvaluationModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    warning_cases: int
    low_quality_cases: int
    quality: EvaluationQualitySummary
    runtime: EvaluationRuntimeSummary


class EvaluationReport(EvaluationModel):
    summary: EvaluationSummary
    results: List[EvaluationCaseResult] = Field(default_factory=list)
