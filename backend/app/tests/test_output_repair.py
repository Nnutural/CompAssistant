import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.output_repair import repair_output_to_model  # noqa: E402
from app.agents.output_validation import validate_output_against_model  # noqa: E402
from app.schemas.research_runtime import (  # noqa: E402
    CompetitionEligibilityArtifact,
    CompetitionRecommendationArtifact,
    CompetitionTimelineArtifact,
)


LANQIAO = "\u84dd\u6865\u676f\u5168\u56fd\u8f6f\u4ef6\u548c\u4fe1\u606f\u6280\u672f\u4e13\u4e1a\u4eba\u624d\u5927\u8d5b"
ELECTRONICS = "\u5168\u56fd\u5927\u5b66\u751f\u7535\u5b50\u8bbe\u8ba1\u7ade\u8d5b"


class OutputRepairTests(unittest.TestCase):
    def test_repair_extracts_markdown_json_and_normalizes_nested_lists(self) -> None:
        raw_output = """```json
{
  "result": {
    "task_type": "competition_recommendation",
    "profile_summary": "direction=algorithms; grade=freshman; abilities=3",
    "recommendations": [
      {
        "competition_id": 14,
        "competition_name": "\\u84dd\\u6865\\u676f\\u5168\\u56fd\\u8f6f\\u4ef6\\u548c\\u4fe1\\u606f\\u6280\\u672f\\u4e13\\u4e1a\\u4eba\\u624d\\u5927\\u8d5b",
        "match_score": "88.5",
        "reasons": "direction fit, beginner friendly",
        "risk_notes": "needs steady practice, needs template review",
        "focus_tags": "algorithms, coding"
      }
    ],
    "risk_overview": "needs steady practice, needs template review"
  }
}
```"""

        repaired = repair_output_to_model(raw_output, CompetitionRecommendationArtifact)
        validation = validate_output_against_model(repaired.repaired_output, CompetitionRecommendationArtifact)

        self.assertEqual(repaired.parse_errors, [])
        self.assertTrue(any("Unwrapped payload" in warning for warning in repaired.warnings))
        self.assertIsNotNone(validation.validated_output)
        artifact = validation.validated_output
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.recommendations[0].focus_tags, ["algorithms", "coding"])
        self.assertEqual(
            artifact.recommendations[0].risk_notes,
            ["needs steady practice", "needs template review"],
        )

    def test_repair_maps_provider_task_type_aliases_for_eligibility_outputs(self) -> None:
        raw_output = {
            "task_type": "eligibility_check",
            "competition_id": 10,
            "competition_name": ELECTRONICS,
            "eligibility_label": "recommended",
            "is_eligible": True,
            "missing_conditions": [],
            "attention_points": ["confirm rules", "confirm team size"],
            "rationale": ["current profile matches the baseline rules"],
        }

        repaired = repair_output_to_model(raw_output, CompetitionEligibilityArtifact)
        validation = validate_output_against_model(repaired.repaired_output, CompetitionEligibilityArtifact)

        self.assertIn(
            "Mapped literal alias for 'task_type' from 'eligibility_check' to 'competition_eligibility_check'.",
            repaired.warnings,
        )
        self.assertIsNotNone(validation.validated_output)
        artifact = validation.validated_output
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.task_type, "competition_eligibility_check")

    def test_repair_recovers_nested_competition_and_score_aliases(self) -> None:
        raw_output = {
            "task_type": "competition_recommend",
            "profile_summary": "good for algorithm track students",
            "recommendations": [
                {
                    "competition": {
                        "id": 14,
                        "name": LANQIAO,
                    },
                    "score": 91.2,
                    "reasons": ["direction fit", "practice material available"],
                    "risk_notes": ["needs steady practice"],
                    "focus_tags": ["algorithms"],
                }
            ],
            "risk_overview": ["time investment is non-trivial"],
        }

        repaired = repair_output_to_model(raw_output, CompetitionRecommendationArtifact)
        validation = validate_output_against_model(repaired.repaired_output, CompetitionRecommendationArtifact)

        self.assertTrue(any("Mapped literal alias" in warning for warning in repaired.warnings))
        self.assertTrue(any("Recovered competition_id" in warning for warning in repaired.warnings))
        self.assertTrue(any("Recovered competition_name" in warning for warning in repaired.warnings))
        self.assertTrue(any("Mapped score to match_score" in warning for warning in repaired.warnings))
        self.assertIsNotNone(validation.validated_output)
        artifact = validation.validated_output
        self.assertIsNotNone(artifact)
        recommendation = artifact.recommendations[0]
        self.assertEqual(recommendation.competition_id, 14)
        self.assertEqual(recommendation.competition_name, LANQIAO)
        self.assertEqual(recommendation.match_score, 91.2)

    def test_repair_fills_missing_task_type_and_flattens_object_risk_overview(self) -> None:
        raw_output = {
            "recommendations": [
                {
                    "id": 14,
                    "name": LANQIAO,
                    "match_score": 93.4,
                    "reasons": ["direction fit", "resources available"],
                    "risk_notes": ["training intensity is high"],
                    "focus_tags": ["algorithms", "coding"],
                    "deadline": "2026-04-05T18:00:00",
                }
            ],
            "risk_overview": {
                "primary_risk": "time investment is high",
                "team_requirements": "needs stable teammates",
            },
        }

        repaired = repair_output_to_model(raw_output, CompetitionRecommendationArtifact)
        validation = validate_output_against_model(repaired.repaired_output, CompetitionRecommendationArtifact)

        self.assertTrue(any("Filled missing task_type" in warning for warning in repaired.warnings))
        self.assertTrue(any("Filled missing profile_summary" in warning for warning in repaired.warnings))
        self.assertTrue(any("Flattened object value into list" in warning for warning in repaired.warnings))
        self.assertTrue(any("Removed unexpected field 'deadline'" in warning for warning in repaired.warnings))
        self.assertIsNotNone(validation.validated_output)
        artifact = validation.validated_output
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.task_type, "competition_recommendation")
        self.assertEqual(
            artifact.risk_overview,
            ["primary_risk: time investment is high", "team_requirements: needs stable teammates"],
        )

    def test_repair_builds_missing_risk_overview_from_recommendation_risks(self) -> None:
        raw_output = {
            "task_type": "competition_recommendation",
            "profile_summary": "algorithm student",
            "recommendations": [
                {
                    "competition_id": 14,
                    "competition_name": LANQIAO,
                    "match_score": 90.0,
                    "reasons": ["direction fit"],
                    "risk_notes": ["training intensity is high", "on-site execution matters"],
                    "focus_tags": ["algorithms"],
                }
            ],
        }

        repaired = repair_output_to_model(raw_output, CompetitionRecommendationArtifact)
        validation = validate_output_against_model(repaired.repaired_output, CompetitionRecommendationArtifact)

        self.assertTrue(any("Filled missing risk_overview" in warning for warning in repaired.warnings))
        self.assertIsNotNone(validation.validated_output)
        artifact = validation.validated_output
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.risk_overview, ["training intensity is high", "on-site execution matters"])

    def test_recommendation_hotfix_normalizes_provider_schema_drift(self) -> None:
        raw_output = {
            "task_type": "algorithm_freshman_competition_recommendation",
            "profile_summary": "suitable for algorithm and coding direction",
            "recommendations": [
                {
                    "competition": {
                        "name": LANQIAO,
                    },
                    "match_score": 92.5,
                    "reasons": ["direction fit", "practice resources are mature"],
                    "risk_notes": ["needs steady practice"],
                    "focus_tags": ["algorithms", "coding"],
                    "difficulty": "medium",
                    "deadline": "2026-04-05T18:00:00",
                    "achievable_ideas": ["idea 1"],
                    "preparation_plan": ["week 1"],
                }
            ],
            "risk_overview": {
                "primary_risk": "needs steady practice",
                "secondary_risk": "team coordination matters",
            },
        }

        repaired = repair_output_to_model(raw_output, CompetitionRecommendationArtifact)
        validation = validate_output_against_model(repaired.repaired_output, CompetitionRecommendationArtifact)

        self.assertIsNotNone(validation.validated_output)
        artifact = validation.validated_output
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.task_type, "competition_recommendation")
        self.assertEqual(artifact.recommendations[0].competition_name, LANQIAO)
        self.assertEqual(artifact.recommendations[0].competition_id, 14)
        self.assertTrue(any("Mapped fuzzy recommendation literal" in warning for warning in repaired.warnings))
        self.assertEqual(
            artifact.risk_overview,
            ["primary_risk: needs steady practice", "secondary_risk: team coordination matters"],
        )
        self.assertTrue(any("Resolved competition_id from competition_name" in warning for warning in repaired.warnings))
        self.assertTrue(any("Removed unexpected field 'difficulty'" in warning for warning in repaired.warnings))
        self.assertTrue(any("Removed unexpected field 'deadline'" in warning for warning in repaired.warnings))
        self.assertTrue(any("Removed unexpected field 'achievable_ideas'" in warning for warning in repaired.warnings))
        self.assertTrue(any("Removed unexpected field 'preparation_plan'" in warning for warning in repaired.warnings))

    def test_timeline_hotfix_unwraps_single_artifact_wrapper(self) -> None:
        raw_output = {
            "competition_timeline_artifact": {
                "competition": {
                    "id": 14,
                    "name": LANQIAO,
                },
                "deadline": "2026-04-10",
                "preparation_checklist": ["lock training slots"],
                "milestones": [
                    {
                        "stage": "基础补齐",
                        "due_at": "2026-03-15",
                        "goals": ["finish core practice set"],
                        "deliverables": ["practice log"],
                    }
                ],
                "stage_plan": ["基础补齐: finish core practice set"],
                "reverse_schedule": ["2026-03-15: 基础补齐 -> practice log"],
                "constraints": {"available_hours_per_week": 6, "team_size": 1, "notes": []},
            }
        }

        repaired = repair_output_to_model(raw_output, CompetitionTimelineArtifact)
        validation = validate_output_against_model(repaired.repaired_output, CompetitionTimelineArtifact)

        self.assertTrue(any("Unwrapped payload from 'competition_timeline_artifact'" in warning for warning in repaired.warnings))
        self.assertIsNotNone(validation.validated_output)
        artifact = validation.validated_output
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.task_type, "competition_timeline_plan")
        self.assertEqual(artifact.competition_id, 14)
        self.assertEqual(artifact.competition_name, LANQIAO)

    def test_validation_marks_empty_recommendations_for_review(self) -> None:
        validation = validate_output_against_model(
            {
                "task_type": "competition_recommendation",
                "profile_summary": "direction=general technology",
                "recommendations": [],
                "risk_overview": [],
            },
            CompetitionRecommendationArtifact,
        )

        self.assertTrue(validation.review_required)
        self.assertIn("recommendations", validation.review_message)


if __name__ == "__main__":
    unittest.main()
