from tests.kernel_api_support import make_registry_tool
from tusk.kernel.agent.agent_tool_catalog import AgentToolCatalog
from tusk.kernel.tool_registry import ToolRegistry


def test_registry_tracks_sequence_callable_tools() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type", sequence_callable=True))
    registry.register(make_registry_tool("gnome.list_windows", "list"))
    assert registry.sequence_tool_names() == {"gnome.type_text"}


def test_catalog_exposes_sequence_callable_flag() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type", sequence_callable=True))
    tool = AgentToolCatalog(registry).list_tools().data["tools"][0]
    assert tool["sequence_callable"] is True
