from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.runtime_modes import resolve_runtime_mode  # noqa: E402
from app.services.evaluation_service import run_evaluation_suite  # noqa: E402


def _parse_runtime_mode(raw_mode: str) -> str:
    return resolve_runtime_mode(raw_mode).normalized_runtime_mode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local evaluation datasets for the agent runtime.")
    parser.add_argument("--task-type", default=None, help="Optional task type filter.")
    parser.add_argument(
        "--runtime-mode",
        default="mock",
        help="Runtime mode to use. Supported values: mock, agents_sdk. The old 'live' alias is no longer accepted.",
    )
    parser.add_argument(
        "--sample-per-task-type",
        type=int,
        default=None,
        help="Optional cap for cases per task type. Useful for agents_sdk spot checks.",
    )
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON.")
    args = parser.parse_args()

    try:
        runtime_mode = _parse_runtime_mode(args.runtime_mode)
    except ValueError as exc:
        parser.error(str(exc))

    report = run_evaluation_suite(
        task_type=args.task_type,
        runtime_mode=runtime_mode,
        sample_per_task_type=args.sample_per_task_type,
    )
    if args.json:
        print(report.model_dump_json(indent=2, ensure_ascii=False))
    else:
        runtime = report.summary.runtime
        print(
            "Evaluation summary:",
            f"mode={runtime.requested_runtime_mode}",
            f"total={report.summary.total_cases}",
            f"passed={report.summary.passed_cases}",
            f"failed={report.summary.failed_cases}",
            f"warning_cases={report.summary.warning_cases}",
            f"low_quality_cases={report.summary.low_quality_cases}",
            f"avg_quality={report.summary.quality.average_score:.3f}",
            f"direct_success_rate={runtime.direct_success_rate:.3f}",
            f"structured_direct_success_rate={runtime.structured_direct_success_rate:.3f}",
            f"json_fallback_success_rate={runtime.json_fallback_success_rate:.3f}",
            f"mock_fallback_success_rate={runtime.mock_fallback_success_rate:.3f}",
            f"provider_structured_success_rate={runtime.provider_structured_success_rate:.3f}",
            f"provider_plain_json_success_rate={runtime.provider_plain_json_success_rate:.3f}",
            f"fallback_rate={runtime.fallback_rate:.3f}",
            f"hard_failure_rate={runtime.hard_failure_rate:.3f}",
            f"awaiting_review_ratio={runtime.awaiting_review_ratio:.3f}",
            f"artifact_completeness_ratio={runtime.artifact_completeness_ratio:.3f}",
            f"avg_latency_ms={runtime.avg_latency_ms:.2f}",
            f"p95_latency_ms={runtime.p95_latency_ms:.2f}",
        )
        print("Error buckets:", runtime.error_bucket_counts)
        print(
            "Detailed issue counts:",
            f"structured_parse_error={runtime.structured_parse_error_count}",
            f"json_fallback_parse_error={runtime.json_fallback_parse_error_count}",
            f"post_normalization_validation_issue={runtime.post_normalization_validation_issue_count}",
            f"timeout={runtime.timeout_error_count}",
        )
        if runtime.error_bucket_examples:
            print("Error examples:")
            for bucket, example in runtime.error_bucket_examples.items():
                print(f"  - {bucket}: {example}")
        for item in report.results:
            warning_text = f" warnings={len(item.warnings)}" if item.warnings else ""
            missing_text = f" missing={','.join(item.missing_fields)}" if item.missing_fields else ""
            quality_text = f" quality={item.quality_score:.3f}/{item.quality_threshold:.3f}"
            quality_fail_text = (
                f" failed_checks={','.join(item.failed_quality_checks)}"
                if item.failed_quality_checks
                else ""
            )
            runtime_text = (
                f" requested={item.requested_runtime_mode}"
                f" effective={item.effective_runtime_mode}"
                f" model={item.effective_model}"
            )
            path_text = f" path={item.completion_path}"
            provider_path_text = (
                f" provider_path={item.provider_success_path}"
                if item.provider_success_path is not None
                else ""
            )
            fallback_text = " fallback=true" if item.used_mock_fallback else ""
            latency_text = f" latency_ms={item.elapsed_ms:.2f}" if item.elapsed_ms is not None else ""
            artifact_text = f" artifact_complete={str(item.artifact_complete).lower()}"
            bucket_text = f" error_buckets={','.join(item.error_buckets)}" if item.error_buckets else ""
            print(
                f"- {item.id}: passed={str(item.passed).lower()} status={item.status}{path_text}"
                f"{provider_path_text}{runtime_text}{fallback_text}{latency_text}{artifact_text}{quality_text}{warning_text}{missing_text}{quality_fail_text}{bucket_text}"
            )
    return 0 if report.summary.failed_cases == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
