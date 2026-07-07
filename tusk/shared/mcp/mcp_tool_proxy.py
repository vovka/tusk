from tusk.shared.schemas.tools.tool_result import ToolResult

__all__ = ["MCPToolProxy"]


class MCPToolProxy:
    def __init__(
        self, source: str, schema: object, client: object,
        planner_visible: bool = True, sequence_callable: bool = False,
    ) -> None:
        self.name = f"{source}.{schema.name}"
        self.description = schema.description
        self.input_schema = schema.input_schema
        self.source = source
        self.planner_visible = planner_visible
        self.sequence_callable = sequence_callable
        self._tool_name = schema.name
        self._client = client

    def execute(self, parameters: dict) -> ToolResult:
        try:
            result = self._client.call_tool(self._tool_name, parameters)
        except Exception as exc:
            return ToolResult(False, f"tool execution failed: {exc}")
        return ToolResult(not result.is_error, result.content, result.data)
