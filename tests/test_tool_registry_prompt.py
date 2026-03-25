import types

from tests.kernel_api_support import make_registry_tool
from tusk.kernel.tool_registry import ToolRegistry


def test_tool_registry_builds_native_tool_definitions_for_broker_and_described_tools() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("find_tools", "discover", broker=True, prompt_visible=True))
    registry.register(make_registry_tool("gnome.close_window", "Close a window"))
    registry.register(make_registry_tool("gnome.list_windows", "List windows"))
    tools = registry.visible_tool_definitions({"gnome.close_window"})
    names = [item["function"]["name"] for item in tools]
    assert "find_tools" in names and "gnome.close_window" in names
    assert "gnome.list_windows" not in names
