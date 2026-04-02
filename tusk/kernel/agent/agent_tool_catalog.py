import json

from tusk.shared.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry

__all__ = ["AgentToolCatalog"]


class AgentToolCatalog:
    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._registry = tool_registry

    def list_tools(self) -> ToolResult:
        tools = [self._info(tool) for tool in self._registry.planner_tools()]
        return ToolResult(True, json.dumps({"tools": tools}), {"tools": tools})

    def prompt_text(self) -> str:
        return f"Tool catalog: {self.list_tools().message}"

    def _info(self, tool: object) -> dict[str, object]:
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
            "source": tool.source,
            "sequence_callable": tool.sequence_callable,
        }
