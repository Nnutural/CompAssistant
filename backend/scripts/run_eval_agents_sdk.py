from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.evaluation_service import run_evaluation_suite  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a focused evaluation suite against the Ark Agents SDK runtime."
    )
    parser.add_argument("--task-type", default=None, help="Optional task type filter.")
    parser.add_argument(
        "--sample-per-task-type",
        type=int,
        default=5,
        help="How many cases to sample per task type. Default: 5.",
    )
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON.")
    args = parser.parse_args()

    report = run_evaluation_suite(
        task_type=args.task_type,
        runtime_mode="agents_sdk",
        sample_per_task_type=args.sample_per_task_type,
    )
    if args.json:
        print(report.model_dump_json(indent=2, ensure_ascii=False))
    else:
        runtime = report.summary.runtime
        print("Agents SDK evaluation summary:")
        print(
            f"mode={runtime.requested_runtime_mode} total={report.summary.total_cases} passed={report.summary.passed_cases} "
            f"failed={report.summary.failed_cases} warning_cases={report.summary.warning_cases} "
            f"avg_quality={report.summary.quality.average_score:.3f}"
        )
        print(
            f"direct_success_rate={runtime.direct_success_rate:.3f} "
            f"structured_direct_success_rate={runtime.structured_direct_success_rate:.3f} "
            f"json_fallback_success_rate={runtime.json_fallback_success_rate:.3f} "
            f"mock_fallback_success_rate={runtime.mock_fallback_success_rate:.3f} "
            f"fallback_rate={runtime.fallback_rate:.3f} "
            f"provider_structured_success_rate={runtime.provider_structured_success_rate:.3f} "
            f"provider_plain_json_success_rate={runtime.provider_plain_json_success_rate:.3f} "
            f"hard_failure_rate={runtime.hard_failure_rate:.3f} awaiting_review_ratio={runtime.awaiting_review_ratio:.3f} "
            f"artifact_completeness_ratio={runtime.artifact_completeness_ratio:.3f} "
            f"avg_latency_ms={runtime.avg_latency_ms:.2f} p95_latency_ms={runtime.p95_latency_ms:.2f}"
        )
        print(f"error_bucket_counts={runtime.error_bucket_counts}")
        print(
            "detailed_issue_counts="
            f"structured_parse_error={runtime.structured_parse_error_count} "
            f"json_fallback_parse_error={runtime.json_fallback_parse_error_count} "
            f"post_normalization_validation_issue={runtime.post_normalization_validation_issue_count} "
            f"timeout={runtime.timeout_error_count}"
        )
        if runtime.error_bucket_examples:
            print("error_bucket_examples:")
            for bucket, example in runtime.error_bucket_examples.items():
                print(f"  - {bucket}: {example}")
        for item in report.results:
            print(
                f"- {item.id}: status={item.status} path={item.completion_path} "
                f"provider_path={item.provider_success_path} "
                f"effective={item.effective_runtime_mode} fallback={str(item.used_mock_fallback).lower()} "
                f"latency_ms={(item.elapsed_ms or 0.0):.2f} quality={item.quality_score:.3f}/{item.quality_threshold:.3f} "
                f"error_buckets={','.join(item.error_buckets)}"
            )
    return 0 if report.summary.failed_cases == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
