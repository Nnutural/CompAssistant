import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.evaluation_service import load_evaluation_cases, run_evaluation_suite  # noqa: E402


class EvaluationRegressionTests(unittest.TestCase):
    def test_eval_datasets_cover_all_phase4b_task_types(self) -> None:
        cases = load_evaluation_cases()
        self.assertEqual(len(cases), 30)

        by_task_type: dict[str, int] = {}
        for case in cases:
            by_task_type[case.task_type] = by_task_type.get(case.task_type, 0) + 1

        self.assertGreaterEqual(by_task_type.get("competition_recommendation", 0), 10)
        self.assertGreaterEqual(by_task_type.get("competition_eligibility_check", 0), 10)
        self.assertGreaterEqual(by_task_type.get("competition_timeline_plan", 0), 10)

    def test_mock_eval_regression_suite_passes_without_failed_cases(self) -> None:
        report = run_evaluation_suite(runtime_mode="mock")

        self.assertEqual(report.summary.total_cases, 30)
        self.assertEqual(report.summary.failed_cases, 0)
        self.assertEqual(report.summary.passed_cases, 30)
        self.assertGreater(report.summary.quality.average_score, 0.7)
        self.assertGreaterEqual(report.summary.quality.highest_score, report.summary.quality.lowest_score)
        self.assertLessEqual(report.summary.low_quality_cases, 2)
        self.assertEqual(report.summary.runtime.requested_runtime_mode, "mock")
        self.assertEqual(report.summary.runtime.direct_success_rate, 0.0)
        self.assertEqual(report.summary.runtime.structured_direct_success_rate, 0.0)
        self.assertEqual(report.summary.runtime.json_fallback_success_rate, 0.0)
        self.assertEqual(report.summary.runtime.mock_fallback_success_rate, 0.0)
        self.assertEqual(report.summary.runtime.provider_structured_success_rate, 0.0)
        self.assertEqual(report.summary.runtime.provider_plain_json_success_rate, 0.0)
        self.assertEqual(report.summary.runtime.fallback_rate, 0.0)
        self.assertEqual(report.summary.runtime.hard_failure_rate, 0.0)
        self.assertGreater(report.summary.runtime.artifact_completeness_ratio, 0.9)
        self.assertEqual(report.summary.runtime.structured_parse_error_count, 0)
        self.assertEqual(report.summary.runtime.json_fallback_parse_error_count, 0)
        self.assertEqual(report.summary.runtime.post_normalization_validation_issue_count, 0)
        self.assertEqual(report.summary.runtime.timeout_error_count, 0)
        self.assertEqual(
            report.summary.runtime.error_bucket_counts,
            {
                "schema_compatibility_error": 0,
                "provider_exception": 0,
                "parse_error": 0,
                "validation_error": 0,
                "fallback_to_mock": 0,
                "hard_failed": 0,
            },
        )
        self.assertEqual(report.summary.runtime.error_bucket_examples, {})
        self.assertTrue(all(result.passed for result in report.results))
        self.assertTrue(all(result.quality_score >= result.quality_threshold for result in report.results))
        self.assertTrue(all(result.completion_path in {"mock", "awaiting_review"} for result in report.results))
        self.assertTrue(all(result.provider_success_path is None for result in report.results))


if __name__ == "__main__":
    unittest.main()
