from tusk.shared.mcp.mcp_stdio_server import tool_schema

__all__ = ["ToolSchemaCatalog"]

_DEFINITIONS = [
    ("launch_application", "Launch an application", {"application_name": "string"}),
    ("close_window", "Close a window", {"window_title": "string"}),
    ("focus_window", "Focus a window", {"window_title": "string"}),
    ("maximize_window", "Maximize a window", {"window_title": "string"}),
    ("minimize_window", "Minimize a window", {"window_title": "string"}),
    ("move_resize_window", "Move and resize a window. geometry is X,Y,WIDTH,HEIGHT in desktop pixels, e.g. 0,0,1440,1800", {"window_title": "string", "geometry": "string"}),
    ("tile_window", "Tile a window to the left or right half of its screen. side is left or right", {"window_title": "string", "side": "string"}),
    ("switch_workspace", "Switch workspace", {"workspace_number": "string"}),
    ("press_keys", "Press keys", {"keys": "string"}),
    ("type_text", "Type text", {"text": "string"}),
    ("replace_recent_text", "Replace recent text", {"replace_chars": "string", "text": "string"}),
    ("mouse_click", "Mouse click", {"x": "string", "y": "string", "button": "string", "clicks": "string"}),
    ("mouse_move", "Mouse move", {"x": "string", "y": "string"}),
    ("mouse_drag", "Mouse drag", {"from_x": "string", "from_y": "string", "to_x": "string", "to_y": "string", "button": "string"}),
    ("mouse_scroll", "Mouse scroll", {"direction": "string", "clicks": "string"}),
    ("read_clipboard", "Read clipboard", {}),
    ("write_clipboard", "Write clipboard", {"text": "string"}),
    ("open_uri", "Open URI", {"uri": "string"}),
    ("get_desktop_context", "Get desktop context", {}),
    ("get_active_window", "Get the active window title, app name, and geometry", {}),
    ("list_windows", "List the currently open windows with app names and geometry", {}),
    ("search_applications", "Search installed desktop applications by name or exec command", {"query": "string"}),
]


class ToolSchemaCatalog:
    def build(self) -> dict[str, dict]:
        return {name: tool_schema(name, description, fields, required=True) for name, description, fields in _DEFINITIONS}
