from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

try:
    from agents import AgentOutputSchema, AgentOutputSchemaBase, function_tool
    from agents.exceptions import UserError
except ImportError:
    AgentOutputSchema = None
    AgentOutputSchemaBase = object
    UserError = RuntimeError
    function_tool = None


class StaticAgentOutputSchema(AgentOutputSchemaBase):  # type: ignore[misc]
    def __init__(
        self,
        *,
        base_schema: Any,
        json_schema_payload: dict[str, Any],
        strict_json_schema: bool,
        debug_metadata: dict[str, Any] | None = None,
    ) -> None:
        self._base_schema = base_schema
        self._json_schema_payload = json_schema_payload
        self._strict_json_schema = strict_json_schema
        self.debug_metadata = debug_metadata or {}

    def is_plain_text(self) -> bool:
        return False

    def json_schema(self) -> dict[str, Any]:
        return deepcopy(self._json_schema_payload)

    def is_strict_json_schema(self) -> bool:
        return self._strict_json_schema

    def validate_json(self, json_str: str) -> Any:
        return self._base_schema.validate_json(json_str)

    def name(self) -> str:
        return self._base_schema.name()


def sanitize_provider_json_schema(schema: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    payload = deepcopy(schema)
    changes: list[str] = []
    strip_keys = {"title", "default", "examples"}

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key in strip_keys:
                if key in node:
                    changes.append(f"{path}.{key}")
                    node.pop(key, None)
            if node.get("type") == "object" and "additionalProperties" in node and node["additionalProperties"] is not False:
                changes.append(f"{path}.additionalProperties")
                node.pop("additionalProperties", None)
            for key, value in list(node.items()):
                _walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                _walk(item, f"{path}[{index}]")

    _walk(payload, "$")
    return payload, changes


def build_provider_output_schema(output_type: type[Any]) -> Any:
    if AgentOutputSchema is None:
        return output_type

    try:
        base_schema = AgentOutputSchema(output_type, strict_json_schema=True)
        schema_payload = base_schema.json_schema()
        sanitized_schema, changes = sanitize_provider_json_schema(schema_payload)
        if not changes:
            setattr(base_schema, "debug_metadata", {"schema_mode": "strict", "schema_changes": []})
            return base_schema
        return StaticAgentOutputSchema(
            base_schema=base_schema,
            json_schema_payload=sanitized_schema,
            strict_json_schema=base_schema.is_strict_json_schema(),
            debug_metadata={"schema_mode": "strict_sanitized", "schema_changes": changes},
        )
    except UserError:
        base_schema = AgentOutputSchema(output_type, strict_json_schema=False)
        sanitized_schema, changes = sanitize_provider_json_schema(base_schema.json_schema())
        return StaticAgentOutputSchema(
            base_schema=base_schema,
            json_schema_payload=sanitized_schema,
            strict_json_schema=False,
            debug_metadata={"schema_mode": "non_strict_sanitized", "schema_changes": changes},
        )


def provider_function_tool(
    *,
    name_override: str | None = None,
    description_override: str | None = None,
    timeout: float | None = None,
) -> Callable[[Callable[..., Any]], Any]:
    if function_tool is None:
        raise RuntimeError("openai-agents is not installed")

    def _decorator(func: Callable[..., Any]) -> Any:
        tool = function_tool(
            name_override=name_override,
            description_override=description_override,
            strict_mode=False,
            timeout=timeout,
        )(func)
        sanitized_schema, changes = sanitize_provider_json_schema(tool.params_json_schema)
        tool.params_json_schema = sanitized_schema
        tool.strict_json_schema = False
        setattr(tool, "_provider_schema_mode", "non_strict_sanitized")
        setattr(tool, "_provider_schema_changes", changes)
        return tool

    return _decorator


def collect_agent_schema_debug(agent: Any) -> dict[str, Any]:
    output_schema_debug: dict[str, Any] | None = None
    output_type = getattr(agent, "output_type", None)
    if output_type is not None and output_type is not str:
        output_schema = output_type
        if AgentOutputSchema is not None and not isinstance(output_schema, AgentOutputSchemaBase):
            output_schema = build_provider_output_schema(output_schema)
        if isinstance(output_schema, AgentOutputSchemaBase):
            output_schema_debug = {
                "name": output_schema.name(),
                "strict_json_schema": output_schema.is_strict_json_schema(),
                "schema": output_schema.json_schema(),
                "debug_metadata": getattr(output_schema, "debug_metadata", {}),
            }

    tools_debug: list[dict[str, Any]] = []
    for tool in getattr(agent, "tools", []) or []:
        schema = getattr(tool, "params_json_schema", None)
        if schema is None:
            continue
        tools_debug.append(
            {
                "name": getattr(tool, "name", type(tool).__name__),
                "strict_json_schema": bool(getattr(tool, "strict_json_schema", False)),
                "schema": deepcopy(schema),
                "schema_mode": getattr(tool, "_provider_schema_mode", "native"),
                "schema_changes": list(getattr(tool, "_provider_schema_changes", [])),
            }
        )

    return {
        "agent_name": getattr(agent, "name", type(agent).__name__),
        "output_schema": output_schema_debug,
        "tools": tools_debug,
    }
