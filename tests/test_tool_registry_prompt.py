import types

from tests.kernel_api_support import make_registry_tool
from tusk.kernel.tool_registry import ToolRegistry


def test_tool_registry_renders_json_schema_text() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.close_window", "closed"))
    registry.get("gnome.close_window")
    text = registry.build_schema_text()
    assert "Tool: gnome.close_window" in text
    assert '"type": "object"' in text
