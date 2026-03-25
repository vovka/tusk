from tusk.kernel.schemas.tool_result import ToolResult

__all__ = ["ToolCallExecutor"]


class ToolCallExecutor:
    def __init__(self, tool_registry: object) -> None:
        self._registry = tool_registry

    def execute(self, tool_call: object, allowed: set[str]) -> ToolResult:
        if tool_call.tool_name not in allowed:
            return ToolResult(False, "That tool is not available in this execution session.")
        return self._executed(tool_call)

    def _executed(self, tool_call: object) -> ToolResult:
        try:
            result = self._registry.get(tool_call.tool_name).execute(tool_call.parameters)
        except KeyError:
            return ToolResult(False, f"unknown tool: {tool_call.tool_name}")
        return result
