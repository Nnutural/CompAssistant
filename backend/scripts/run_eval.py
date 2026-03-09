from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.evaluation_service import run_evaluation_suite  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local evaluation datasets for the agent runtime.")
    parser.add_argument("--task-type", default=None, help="Optional task type filter.")
    parser.add_argument("--runtime-mode", default="mock", help="Runtime mode to use. Default: mock.")
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON.")
    args = parser.parse_args()

    report = run_evaluation_suite(task_type=args.task_type, runtime_mode=args.runtime_mode)
    if args.json:
        print(report.model_dump_json(indent=2, ensure_ascii=False))
    else:
        print(
            "Evaluation summary:",
            f"total={report.summary.total_cases}",
            f"passed={report.summary.passed_cases}",
            f"failed={report.summary.failed_cases}",
            f"warning_cases={report.summary.warning_cases}",
        )
        for item in report.results:
            warning_text = f" warnings={len(item.warnings)}" if item.warnings else ""
            missing_text = f" missing={','.join(item.missing_fields)}" if item.missing_fields else ""
            print(
                f"- {item.id}: passed={str(item.passed).lower()} status={item.status}{warning_text}{missing_text}"
            )
    return 0 if report.summary.failed_cases == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
