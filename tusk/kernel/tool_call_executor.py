from tusk.kernel.schemas.tool_result import ToolResult

__all__ = ["ToolCallExecutor"]


class ToolCallExecutor:
    def __init__(self, tool_registry: object, usage_recorder: object) -> None:
        self._registry = tool_registry
        self._usage = usage_recorder

    def execute(self, tool_call: object, described: set[str]) -> ToolResult:
        if not self._registry.can_call_described(tool_call.tool_name, described):
            return ToolResult(False, "Describe the tool before calling it directly.")
        return self._executed(tool_call)

    def _executed(self, tool_call: object) -> ToolResult:
        try:
            result = self._registry.get(tool_call.tool_name).execute(tool_call.parameters)
        except KeyError:
            return ToolResult(False, f"unknown tool: {tool_call.tool_name}")
        self._usage.record(tool_call.tool_name, result)
        return result
