import json

from tusk.kernel.schemas.tool_result import ToolResult

__all__ = ["DescribeToolTool"]


class DescribeToolTool:
    source = "kernel"
    broker = True
    prompt_visible = True
    name = "describe_tool"
    description = "Describe one tool and its exact arguments"
    input_schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}

    def __init__(self, tool_registry: object) -> None:
        self._registry = tool_registry

    def execute(self, parameters: dict) -> ToolResult:
        name = str(parameters.get("name", "")).strip()
        if not name:
            return ToolResult(False, "describe_tool requires a tool name")
        return self._described(name)

    def _described(self, name: str) -> ToolResult:
        try:
            tool = self._registry.get(name)
        except KeyError:
            return ToolResult(False, f"unknown tool: {name}")
        return ToolResult(True, "\n".join(self._lines(tool)))

    def _lines(self, tool: object) -> list[str]:
        return [
            f"Tool: {tool.name}",
            f"Description: {tool.description}",
            f"Schema: {json.dumps(tool.input_schema, sort_keys=True)}",
            f"run_tool example: {{\"name\":\"{tool.name}\",\"input_json\":\"{self._example(tool)}\"}}",
        ]

    def _example(self, tool: object) -> str:
        sample = {key: f"<{key}>" for key in tool.input_schema.get("properties", {})}
        return json.dumps(sample, sort_keys=True).replace('"', '\\"')
