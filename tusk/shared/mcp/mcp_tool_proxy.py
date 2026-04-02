from tusk.shared.schemas.tool_result import ToolResult

__all__ = ["MCPToolProxy"]

_INTERNAL_TOOL_NAMES = {"dictation.start_dictation", "dictation.stop_dictation"}
_SEQUENCE_TOOL_NAMES = {
    "gnome.close_window",
    "gnome.focus_window",
    "gnome.maximize_window",
    "gnome.minimize_window",
    "gnome.move_resize_window",
    "gnome.switch_workspace",
    "gnome.press_keys",
    "gnome.type_text",
    "gnome.replace_recent_text",
    "gnome.mouse_click",
    "gnome.mouse_move",
    "gnome.mouse_drag",
    "gnome.mouse_scroll",
    "gnome.write_clipboard",
}


class MCPToolProxy:
    def __init__(self, source: str, schema: object, client: object, runner: object) -> None:
        self.name = f"{source}.{schema.name}"
        self.description = schema.description
        self.input_schema = schema.input_schema
        self.source = source
        self.planner_visible = self.name not in _INTERNAL_TOOL_NAMES
        self.sequence_callable = self.name in _SEQUENCE_TOOL_NAMES
        self._tool_name = schema.name
        self._client = client
        self._runner = runner

    def execute(self, parameters: dict) -> ToolResult:
        try:
            result = self._runner(self._client.call_tool(self._tool_name, parameters))
        except Exception as exc:
            return ToolResult(False, f"tool execution failed: {exc}")
        return ToolResult(not result.is_error, result.content, result.data)
