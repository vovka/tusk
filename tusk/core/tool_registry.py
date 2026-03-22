import json

from tusk.interfaces.agent_tool import AgentTool

__all__ = ["ToolRegistry"]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool:
        return self._tools[name]

    def all_tools(self) -> list[AgentTool]:
        return list(self._tools.values())

    def build_schema_text(self) -> str:
        lines = [self._tool_schema(t) for t in self._tools.values()]
        return "\n".join(lines)

    def _tool_schema(self, tool: AgentTool) -> str:
        schema = {"tool": tool.name, **tool.parameters_schema}
        return json.dumps(schema)
