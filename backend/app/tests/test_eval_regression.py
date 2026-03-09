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
        self.assertTrue(all(result.passed for result in report.results))


if __name__ == "__main__":
    unittest.main()
