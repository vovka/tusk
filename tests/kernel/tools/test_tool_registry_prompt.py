from tests.support.kernel_api import make_registry_tool
from tusk.kernel.tools.tool_registry import ToolRegistry


def test_tool_registry_returns_planner_visible_tools_only() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("execute_task", "Execute a task", planner_visible=False))
    registry.register(make_registry_tool("gnome.close_window", "Close a window"))
    registry.register(make_registry_tool("gnome.list_windows", "List windows"))
    names = [tool.name for tool in registry.planner_tools()]
    assert "gnome.close_window" in names
    assert "gnome.list_windows" in names
    assert "execute_task" not in names


def test_tool_registry_builds_native_definitions_for_selected_tools() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.close_window", "Close a window"))
    registry.register(make_registry_tool("gnome.list_windows", "List windows"))
    tools = registry.definitions_for({"gnome.close_window"})
    names = [item["function"]["name"] for item in tools]
    assert "gnome.close_window" in names
    assert "gnome.list_windows" not in names
