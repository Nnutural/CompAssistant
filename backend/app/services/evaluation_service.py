from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any

from app.repositories.ledger_repository import LedgerRepository
from app.schemas.agent_tasks import AgentTaskCreateRequest, AgentTaskStatusResponse
from app.schemas.evaluation import (
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationQualitySummary,
    EvaluationReport,
    EvaluationRuntimeSummary,
    EvaluationSummary,
)
from app.services.research_runtime_service import ResearchRuntimeService
from app.tools.competition_runtime import (
    build_timeline_template,
    check_eligibility_rules,
    filter_competitions_by_profile,
    unwrap_tool_result,
)


EVAL_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "evals"
DEFAULT_QUALITY_THRESHOLDS = {
    "competition_recommendation": 0.66,
    "competition_eligibility_check": 0.7,
    "competition_timeline_plan": 0.68,
}
DEFAULT_MIN_CHECK_SCORE = 0.55


def load_evaluation_cases(task_type: str | None = None) -> list[EvaluationCase]:
    files = sorted(EVAL_DATA_DIR.glob("*.json"))
    cases: list[EvaluationCase] = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cases.extend(EvaluationCase.model_validate(item) for item in payload)
    if task_type:
        return [case for case in cases if case.task_type == task_type]
    return cases


def run_evaluation_suite(
    task_type: str | None = None,
    *,
    runtime_mode: str = "mock",
    sample_per_task_type: int | None = None,
) -> EvaluationReport:
    cases = load_evaluation_cases(task_type=task_type)
    if sample_per_task_type is not None:
        cases = _sample_cases_by_task_type(cases, sample_per_task_type)

    with tempfile.TemporaryDirectory() as temp_dir:
        service = ResearchRuntimeService(
            repository=LedgerRepository(temp_dir),
            runtime_mode=runtime_mode,
        )
        try:
            results = [run_evaluation_case(case, service) for case in cases]
        finally:
            service.shutdown(wait=True)

    scores = [item.quality_score for item in results] or [0.0]
    runtime_summary = _build_runtime_summary(results, runtime_mode=runtime_mode)
    summary = EvaluationSummary(
        total_cases=len(results),
        passed_cases=sum(1 for item in results if item.passed),
        failed_cases=sum(1 for item in results if not item.passed),
        warning_cases=sum(1 for item in results if item.warnings),
        low_quality_cases=sum(1 for item in results if item.quality_score < item.quality_threshold),
        quality=EvaluationQualitySummary(
            average_score=round(sum(scores) / len(scores), 4),
            lowest_score=round(min(scores), 4),
            highest_score=round(max(scores), 4),
        ),
        runtime=runtime_summary,
    )
    return EvaluationReport(summary=summary, results=results)


def run_evaluation_case(case: EvaluationCase, service: ResearchRuntimeService) -> EvaluationCaseResult:
    payload = dict(case.input)
    payload.setdefault("task_type", case.task_type)
    request = AgentTaskCreateRequest.model_validate(payload)
    if request.task_id is None:
        request = request.model_copy(update={"task_id": f"eval-{case.id}"})
    status = service.create_agent_task(request)
    status = _wait_for_terminal_status(service, status.run_id)
    artifacts = service.get_task_artifacts(status.run_id)

    artifact_payload = {}
    artifact_complete = False
    if artifacts and artifacts.items:
        artifact_payload = artifacts.items[0].payload or {}
        artifact_complete = bool(artifact_payload)

    missing_fields = [
        field_path
        for field_path in case.expected_required_fields
        if _is_missing_required_field(artifact_payload, field_path)
    ]
    rubric_missing_fields = [
        field_path
        for field_path in case.scoring_rubric.get("require_non_empty", [])
        if _is_missing_required_field(artifact_payload, field_path)
    ]
    for field_path in rubric_missing_fields:
        if field_path not in missing_fields:
            missing_fields.append(field_path)

    quality_score, quality_threshold, failed_quality_checks = _evaluate_quality(case, artifact_payload)

    warnings: list[str] = []
    for field_path in rubric_missing_fields:
        warnings.append(f"scoring rubric requires non-empty field: {field_path}")
    for check_name in failed_quality_checks:
        warnings.append(f"quality check below threshold: {check_name}")
    if status.status == "awaiting_review":
        warnings.append("run entered awaiting_review")
    if status.used_mock_fallback:
        warnings.append("mock fallback used")
    if status.result.blockers:
        warnings.extend(status.result.blockers)

    passed = (
        not missing_fields
        and status.status not in {"failed", "cancelled"}
        and quality_score >= quality_threshold
    )
    return EvaluationCaseResult(
        id=case.id,
        task_type=case.task_type,
        run_id=status.run_id,
        passed=passed,
        status=status.status,
        current_state=status.current_state,
        completion_path=_derive_completion_path(status),
        requested_runtime_mode=status.requested_runtime_mode,
        effective_runtime_mode=status.effective_runtime_mode,
        effective_model=status.effective_model,
        used_mock_fallback=status.used_mock_fallback,
        fallback_reason=status.fallback_reason,
        elapsed_ms=status.elapsed_ms,
        artifact_complete=artifact_complete and not missing_fields,
        missing_fields=missing_fields,
        warnings=warnings,
        result_summary=status.result.summary,
        quality_score=quality_score,
        quality_threshold=quality_threshold,
        failed_quality_checks=failed_quality_checks,
    )


def _wait_for_terminal_status(
    service: ResearchRuntimeService,
    run_id: str,
    *,
    timeout_seconds: float = 90.0,
) -> AgentTaskStatusResponse:
    deadline = time.perf_counter() + timeout_seconds
    while time.perf_counter() < deadline:
        status = service.get_task_status(run_id)
        if status is not None and status.status in {"completed", "cancelled", "failed", "awaiting_review"}:
            return status
        time.sleep(0.1)
    raise TimeoutError(f"Timed out waiting for evaluation run to finish: {run_id}")


def _evaluate_quality(case: EvaluationCase, artifact_payload: dict[str, Any]) -> tuple[float, float, list[str]]:
    rubric = case.scoring_rubric or {}
    threshold = float(rubric.get("quality_threshold", DEFAULT_QUALITY_THRESHOLDS.get(case.task_type, 0.65)))
    minimum_check_score = float(rubric.get("minimum_check_score", DEFAULT_MIN_CHECK_SCORE))

    if case.task_type == "competition_recommendation":
        checks = _score_recommendation(case, artifact_payload)
    elif case.task_type == "competition_eligibility_check":
        checks = _score_eligibility(case, artifact_payload)
    elif case.task_type == "competition_timeline_plan":
        checks = _score_timeline(case, artifact_payload)
    else:
        checks = {"baseline_structure": 1.0 if artifact_payload else 0.0}

    score = round(sum(checks.values()) / max(len(checks), 1), 4)
    failed_checks = [name for name, value in checks.items() if value < minimum_check_score]
    return score, threshold, failed_checks


def _score_recommendation(case: EvaluationCase, artifact_payload: dict[str, Any]) -> dict[str, float]:
    profile = _as_dict(case.input.get("payload", {})).get("profile", {})
    recommendations = _as_list(artifact_payload.get("recommendations"))
    if not recommendations:
        return {
            "profile_alignment": 0.0,
            "reason_specificity": 0.0,
            "risk_signal": 0.0,
            "anti_generic": 0.0,
        }

    local_matches = unwrap_tool_result(
        filter_competitions_by_profile(_as_dict(profile)),
        "filter_competitions_by_profile",
    )
    top_expected_ids = [
        _as_dict(item.get("competition")).get("id")
        for item in _as_list(local_matches.get("matches"))[:5]
    ]
    returned_ids = [item.get("competition_id") for item in recommendations[:3]]
    overlap = len({item for item in returned_ids if item in top_expected_ids})
    profile_alignment = _clamp(overlap / max(1, min(3, len(returned_ids))))

    reasons = [text for item in recommendations[:3] for text in _text_list(item.get("reasons"))]
    avg_reason_count = sum(len(_text_list(item.get("reasons"))) for item in recommendations[:3]) / max(
        1,
        min(3, len(recommendations)),
    )
    avg_reason_length = sum(len(text) for text in reasons) / max(1, len(reasons))
    reason_specificity = _clamp(((avg_reason_count / 2.0) + (avg_reason_length / 24.0)) / 2.0)

    risk_notes = _text_list(artifact_payload.get("risk_overview")) + [
        text for item in recommendations[:3] for text in _text_list(item.get("risk_notes"))
    ]
    avg_risk_length = sum(len(text) for text in risk_notes) / max(1, len(risk_notes))
    risk_signal = 0.0 if not risk_notes else _clamp((min(len(risk_notes), 4) / 4.0 + min(avg_risk_length, 28) / 28.0) / 2.0)

    generic_texts = [text.lower().strip() for text in reasons + risk_notes if text.strip()]
    unique_ratio = len(set(generic_texts)) / max(1, len(generic_texts))
    anti_generic = _clamp(unique_ratio)

    return {
        "profile_alignment": round(profile_alignment, 4),
        "reason_specificity": round(reason_specificity, 4),
        "risk_signal": round(risk_signal, 4),
        "anti_generic": round(anti_generic, 4),
    }


def _score_eligibility(case: EvaluationCase, artifact_payload: dict[str, Any]) -> dict[str, float]:
    payload = _as_dict(case.input.get("payload", {}))
    competition_id = int(payload.get("competition_id", 0))
    profile = _as_dict(payload.get("profile", {}))
    expected = unwrap_tool_result(
        check_eligibility_rules(competition_id, profile),
        "check_eligibility_rules",
    )

    artifact_label = artifact_payload.get("eligibility_label")
    label_match = 1.0 if artifact_label == expected.get("eligibility_label") else 0.0
    eligible_match = 1.0 if bool(artifact_payload.get("is_eligible")) == bool(expected.get("is_eligible")) else 0.0
    rule_alignment = (label_match + eligible_match) / 2.0

    expected_missing = _text_list(expected.get("missing_conditions"))
    actual_missing = _text_list(artifact_payload.get("missing_conditions"))
    if not expected_missing:
        missing_specificity = 1.0 if not actual_missing else 0.75
    else:
        missing_specificity = 0.4 if not actual_missing else _clamp(len(actual_missing) / len(expected_missing))
        avg_missing_length = sum(len(text) for text in actual_missing) / max(1, len(actual_missing))
        missing_specificity = _clamp((missing_specificity + min(avg_missing_length, 22) / 22.0) / 2.0)

    rationale = _text_list(artifact_payload.get("rationale"))
    attention_points = _text_list(artifact_payload.get("attention_points"))
    grounded_explanation = _clamp(
        (
            (1.0 if rationale else 0.0)
            + (1.0 if attention_points or not _text_list(expected.get("attention_points")) else 0.0)
            + min(sum(len(text) for text in rationale), 60) / 60.0
        )
        / 3.0
    )

    return {
        "rule_alignment": round(rule_alignment, 4),
        "missing_specificity": round(missing_specificity, 4),
        "grounded_explanation": round(grounded_explanation, 4),
    }


def _score_timeline(case: EvaluationCase, artifact_payload: dict[str, Any]) -> dict[str, float]:
    payload = _as_dict(case.input.get("payload", {}))
    competition_id = int(payload.get("competition_id", 0))
    deadline = payload.get("deadline")
    constraints = _as_dict(payload.get("constraints", {}))
    expected = unwrap_tool_result(
        build_timeline_template(competition_id, deadline, constraints),
        "build_timeline_template",
    )

    actual_milestones = _as_list(artifact_payload.get("milestones"))
    expected_milestones = _as_list(expected.get("milestones"))
    actual_stage_names = {str(item.get("stage")).strip().lower() for item in actual_milestones if item.get("stage")}
    expected_stage_names = {str(item.get("stage")).strip().lower() for item in expected_milestones if item.get("stage")}
    stage_overlap = len(actual_stage_names.intersection(expected_stage_names)) / max(1, len(expected_stage_names))

    reverse_schedule = _text_list(artifact_payload.get("reverse_schedule"))
    stage_plan = _text_list(artifact_payload.get("stage_plan"))
    due_dates = [str(item.get("due_at")) for item in actual_milestones if item.get("due_at")]
    sorted_dates = sorted(due_dates)
    schedule_reasonableness = _clamp(
        (
            (1.0 if due_dates == sorted_dates else 0.3)
            + (1.0 if len(reverse_schedule) >= len(actual_milestones) else 0.4)
            + (1.0 if stage_plan else 0.0)
        )
        / 3.0
    )

    checklist = _text_list(artifact_payload.get("preparation_checklist"))
    deliverable_coverage = [
        item
        for item in actual_milestones[:3]
        if _text_list(_as_dict(item).get("deliverables"))
    ]
    omission_score = _clamp(
        (
            (1.0 if checklist else 0.0)
            + (len(deliverable_coverage) / max(1, min(3, len(actual_milestones))))
            + (1.0 if actual_milestones else 0.0)
        )
        / 3.0
    )

    return {
        "stage_coverage": round(_clamp(stage_overlap), 4),
        "schedule_reasonableness": round(schedule_reasonableness, 4),
        "omission_check": round(omission_score, 4),
    }


def _sample_cases_by_task_type(cases: list[EvaluationCase], sample_per_task_type: int) -> list[EvaluationCase]:
    if sample_per_task_type <= 0:
        return []
    sampled: list[EvaluationCase] = []
    by_task_type: dict[str, list[EvaluationCase]] = {}
    for case in cases:
        by_task_type.setdefault(case.task_type, []).append(case)
    for task_type in sorted(by_task_type):
        sampled.extend(by_task_type[task_type][:sample_per_task_type])
    return sampled


def _build_runtime_summary(results: list[EvaluationCaseResult], *, runtime_mode: str) -> EvaluationRuntimeSummary:
    total = len(results) or 1
    latencies = sorted(float(item.elapsed_ms) for item in results if item.elapsed_ms is not None)
    direct_success_cases = sum(1 for item in results if item.completion_path == "provider")
    fallback_cases = sum(1 for item in results if item.completion_path == "mock_fallback")
    hard_failure_cases = sum(1 for item in results if item.completion_path in {"failed", "cancelled"})
    awaiting_review_cases = sum(1 for item in results if item.completion_path == "awaiting_review")
    artifact_complete_cases = sum(1 for item in results if item.artifact_complete)

    return EvaluationRuntimeSummary(
        requested_runtime_mode=runtime_mode,
        direct_success_rate=round(direct_success_cases / total, 4),
        fallback_rate=round(fallback_cases / total, 4),
        hard_failure_rate=round(hard_failure_cases / total, 4),
        awaiting_review_ratio=round(awaiting_review_cases / total, 4),
        artifact_completeness_ratio=round(artifact_complete_cases / total, 4),
        avg_latency_ms=round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        p95_latency_ms=_percentile(latencies, 0.95),
    )


def _derive_completion_path(status: AgentTaskStatusResponse) -> str:
    if status.status == "cancelled":
        return "cancelled"
    if status.status == "failed":
        return "failed"
    if status.status == "awaiting_review":
        return "awaiting_review"
    if status.used_mock_fallback:
        return "mock_fallback"
    if status.effective_runtime_mode == "mock":
        return "mock"
    return "provider"


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    index = max(0, min(len(values) - 1, int(round((len(values) - 1) * ratio))))
    return round(values[index], 2)


def _is_missing_required_field(payload: Any, field_path: str) -> bool:
    current = payload
    for part in field_path.split("."):
        if isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return True
            if index >= len(current):
                return True
            current = current[index]
            continue
        if isinstance(current, dict):
            if part not in current:
                return True
            current = current[part]
            continue
        return True

    if current is None:
        return True
    if isinstance(current, str):
        return not current.strip()
    if isinstance(current, list):
        return len(current) == 0
    if isinstance(current, dict):
        return len(current) == 0
    return False


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _as_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [_as_dict(item) for item in value]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
