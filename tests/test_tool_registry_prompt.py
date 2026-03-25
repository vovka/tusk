from tests.kernel_api_support import make_registry_tool
from tusk.kernel.tool_registry import ToolRegistry


def test_tool_registry_builds_planner_catalog_from_visible_real_tools() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("execute_task", "Execute a task", planner_visible=False))
    registry.register(make_registry_tool("gnome.close_window", "Close a window"))
    registry.register(make_registry_tool("gnome.list_windows", "List windows"))
    catalog = registry.build_planner_catalog_text()
    assert "gnome.close_window: Close a window" in catalog
    assert "gnome.list_windows: List windows" in catalog
    assert "execute_task" not in catalog


def test_tool_registry_builds_native_definitions_for_selected_tools() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.close_window", "Close a window"))
    registry.register(make_registry_tool("gnome.list_windows", "List windows"))
    tools = registry.definitions_for({"gnome.close_window"})
    names = [item["function"]["name"] for item in tools]
    assert "gnome.close_window" in names
    assert "gnome.list_windows" not in names
