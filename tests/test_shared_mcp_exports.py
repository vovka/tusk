import tusk.shared.mcp as mcp


def test_shared_mcp_exports_present() -> None:
    assert "AdapterEnvironmentBuilder" in mcp.__all__
    assert "AdapterWatcher" in mcp.__all__
    assert "MCPClient" in mcp.__all__
    assert "MCPToolProxy" in mcp.__all__
