import unittest
import sys
from pathlib import Path

from pydantic import BaseModel

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.schema_adapter import (
    build_provider_output_schema,
    collect_agent_schema_debug,
    provider_function_tool,
    sanitize_provider_json_schema,
)


class _ProfileModel(BaseModel):
    direction: str
    grade: str


class _StructuredOutputModel(BaseModel):
    summary: str
    profile: _ProfileModel


class SchemaAdapterTests(unittest.TestCase):
    def test_sanitize_provider_json_schema_removes_non_false_additional_properties(self) -> None:
        raw_schema = {
            "type": "object",
            "properties": {
                "profile": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {"direction": {"type": "string"}},
                }
            },
            "additionalProperties": True,
        }

        sanitized, changes = sanitize_provider_json_schema(raw_schema)

        self.assertNotIn("additionalProperties", sanitized)
        self.assertNotIn("additionalProperties", sanitized["properties"]["profile"])
        self.assertIn("$.additionalProperties", changes)
        self.assertIn("$.properties.profile.additionalProperties", changes)

    def test_build_provider_output_schema_exposes_debug_metadata(self) -> None:
        output_schema = build_provider_output_schema(_StructuredOutputModel)
        debug = getattr(output_schema, "debug_metadata", {})

        self.assertIn(debug.get("schema_mode"), {"strict", "strict_sanitized", "non_strict_sanitized"})
        self.assertIsInstance(output_schema.json_schema(), dict)

    def test_provider_function_tool_sanitizes_tool_schema(self) -> None:
        @provider_function_tool(name_override="test_tool")
        def test_tool(profile: _ProfileModel) -> dict:
            return {"ok": True}

        self.assertFalse(getattr(test_tool, "strict_json_schema", True))
        self.assertIsInstance(getattr(test_tool, "params_json_schema", None), dict)
        changes = list(getattr(test_tool, "_provider_schema_changes", []))
        self.assertIn(
            getattr(test_tool, "_provider_schema_mode", "native"),
            {"native", "sanitized", "non_strict_sanitized"},
        )
        schema = getattr(test_tool, "params_json_schema", {})
        self.assertIsInstance(schema, dict)
        self.assertNotIn("additionalProperties", str(schema))
        if changes:
            self.assertTrue(any(change.startswith("$") for change in changes))

    def test_collect_agent_schema_debug_reports_sanitized_tool_schema(self) -> None:
        @provider_function_tool(name_override="test_tool")
        def test_tool(profile: _ProfileModel) -> dict:
            return {"ok": True}

        class _FakeAgent:
            name = "fake-agent"
            output_type = _StructuredOutputModel
            tools = [test_tool]

        debug = collect_agent_schema_debug(_FakeAgent())

        self.assertEqual(debug["agent_name"], "fake-agent")
        self.assertEqual(debug["tools"][0]["name"], "test_tool")
        self.assertIn(debug["tools"][0]["schema_mode"], {"non_strict_sanitized", "native"})


if __name__ == "__main__":
    unittest.main()
