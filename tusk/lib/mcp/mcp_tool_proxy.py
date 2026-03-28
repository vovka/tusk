from tusk.kernel.schemas.tool_result import ToolResult

__all__ = ["MCPToolProxy"]

_INTERNAL_TOOL_NAMES = {"dictation.start_dictation", "dictation.stop_dictation"}


class MCPToolProxy:
    def __init__(self, source: str, schema: object, client: object, runner: object) -> None:
        self.name = f"{source}.{schema.name}"
        self.description = schema.description
        self.input_schema = schema.input_schema
        self.source = source
        self.planner_visible = self.name not in _INTERNAL_TOOL_NAMES
        self._tool_name = schema.name
        self._client = client
        self._runner = runner

    def execute(self, parameters: dict) -> ToolResult:
        try:
            result = self._runner(self._client.call_tool(self._tool_name, parameters))
        except Exception as exc:
            return ToolResult(False, f"tool execution failed: {exc}")
        return ToolResult(not result.is_error, result.content, result.data)
