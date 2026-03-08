import json
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.schemas.research_runtime import (  # noqa: E402
    AgentHandoff,
    AgentResult,
    AgentTaskEnvelope,
    ResearchLedger,
)


SCHEMA_CASES = [
    (
        "agent-task-envelope.schema.json",
        "agent-task-envelope.minimal.json",
        AgentTaskEnvelope,
        "AgentTaskEnvelope",
    ),
    (
        "agent-handoff.schema.json",
        "agent-handoff.minimal.json",
        AgentHandoff,
        "AgentHandoff",
    ),
    (
        "agent-result.schema.json",
        "agent-result.minimal.json",
        AgentResult,
        "AgentResult",
    ),
    (
        "research-ledger.schema.json",
        "research-ledger.minimal.json",
        ResearchLedger,
        "ResearchLedger",
    ),
]


class ResearchRuntimeContractTests(unittest.TestCase):
    def _load_json(self, *parts: str) -> dict:
        path = REPO_ROOT.joinpath(*parts)
        with path.open("r", encoding="utf-8-sig") as handle:
            return json.load(handle)

    def test_schema_files_have_expected_top_level_shape(self) -> None:
        for schema_name, _, model_cls, expected_title in SCHEMA_CASES:
            with self.subTest(schema=schema_name):
                schema = self._load_json("docs", "schemas", schema_name)
                model_required = {
                    field_name
                    for field_name, field_info in model_cls.model_fields.items()
                    if field_info.is_required()
                }

                self.assertEqual(schema["title"], expected_title)
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(set(schema["required"]), model_required)
                self.assertEqual(set(schema["properties"].keys()), set(model_cls.model_fields.keys()))

    def test_example_payloads_validate_against_pydantic_models(self) -> None:
        for _, example_name, model_cls, _ in SCHEMA_CASES:
            with self.subTest(example=example_name):
                payload = self._load_json("docs", "examples", example_name)
                model = model_cls.model_validate(payload)
                self.assertEqual(model.contract_version, "1.0")

    def test_phase2_runtime_examples_validate_against_contract_models(self) -> None:
        runtime_input = self._load_json("docs", "examples", "research-runtime-input.minimal.json")
        runtime_result = self._load_json("docs", "examples", "research-runtime-result.minimal.json")

        task = AgentTaskEnvelope.model_validate(runtime_input)
        result = AgentResult.model_validate(runtime_result)

        self.assertEqual(task.contract_version, "1.0")
        self.assertEqual(result.contract_version, "1.0")


if __name__ == "__main__":
    unittest.main()
