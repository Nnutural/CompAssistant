from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from app.repositories.ledger_repository import LedgerRepository
from app.schemas.agent_tasks import AgentTaskCreateRequest
from app.schemas.evaluation import EvaluationCase, EvaluationCaseResult, EvaluationReport, EvaluationSummary
from app.services.research_runtime_service import ResearchRuntimeService


EVAL_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "evals"


def load_evaluation_cases(task_type: str | None = None) -> list[EvaluationCase]:
    files = sorted(EVAL_DATA_DIR.glob("*.json"))
    cases: list[EvaluationCase] = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cases.extend(EvaluationCase.model_validate(item) for item in payload)
    if task_type:
        return [case for case in cases if case.task_type == task_type]
    return cases


def run_evaluation_suite(task_type: str | None = None, *, runtime_mode: str = "mock") -> EvaluationReport:
    cases = load_evaluation_cases(task_type=task_type)
    with tempfile.TemporaryDirectory() as temp_dir:
        service = ResearchRuntimeService(
            repository=LedgerRepository(temp_dir),
            runtime_mode=runtime_mode,
        )
        results = [run_evaluation_case(case, service) for case in cases]

    summary = EvaluationSummary(
        total_cases=len(results),
        passed_cases=sum(1 for item in results if item.passed),
        failed_cases=sum(1 for item in results if not item.passed),
        warning_cases=sum(1 for item in results if item.warnings),
    )
    return EvaluationReport(summary=summary, results=results)


def run_evaluation_case(case: EvaluationCase, service: ResearchRuntimeService) -> EvaluationCaseResult:
    payload = dict(case.input)
    payload.setdefault("task_type", case.task_type)
    request = AgentTaskCreateRequest.model_validate(payload)
    if request.task_id is None:
        request = request.model_copy(update={"task_id": f"eval-{case.id}"})
    status = service.create_agent_task(request)
    artifacts = service.get_task_artifacts(status.run_id)

    artifact_payload = {}
    if artifacts and artifacts.items:
        artifact_payload = artifacts.items[0].payload or {}

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

    warnings: list[str] = []
    for field_path in rubric_missing_fields:
        warnings.append(f"scoring rubric requires non-empty field: {field_path}")
    if status.status == "awaiting_review":
        warnings.append("run entered awaiting_review")
    if status.used_mock_fallback:
        warnings.append("mock fallback used")
    if status.result.blockers:
        warnings.extend(status.result.blockers)

    passed = not missing_fields and status.status != "failed"
    return EvaluationCaseResult(
        id=case.id,
        task_type=case.task_type,
        run_id=status.run_id,
        passed=passed,
        status=status.status,
        current_state=status.current_state,
        missing_fields=missing_fields,
        warnings=warnings,
        result_summary=status.result.summary,
    )


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
