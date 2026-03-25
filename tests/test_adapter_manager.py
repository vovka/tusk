import json
import textwrap
import types

from tusk.kernel.adapter_manager import AdapterManager
from tusk.kernel.tool_registry import ToolRegistry

_MANIFEST = {
    "name": "demo",
    "version": "1.0.0",
    "description": "demo",
    "transport": "stdio",
    "entry": "python server.py",
}
_SERVER = """
import json
import sys

tools = [{"name": "ping", "description": "ping", "inputSchema": {"type": "object", "properties": {}}}]

for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    if method == "initialize":
        payload = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
    elif method == "tools/list":
        payload = {"tools": tools}
    elif method == "tools/call":
        payload = {"content": [{"type": "text", "text": "pong"}], "isError": False}
    else:
        payload = {}
    response = {"jsonrpc": "2.0", "id": request["id"], "result": payload}
    sys.stdout.write(json.dumps(response) + "\\n")
    sys.stdout.flush()
"""


def test_adapter_manager_registers_namespaced_tools(tmp_path) -> None:
    _write_adapter(tmp_path / "demo")
    manager = AdapterManager(str(tmp_path), ToolRegistry(), types.SimpleNamespace(log=lambda *a: None))
    manager.run_async(manager.start_all())
    assert manager.tool_registry.get("demo.ping").name == "demo.ping"


def _write_adapter(adapter_dir) -> None:
    adapter_dir.mkdir()
    (adapter_dir / "adapter.json").write_text(json.dumps(_MANIFEST))
    (adapter_dir / "server.py").write_text(textwrap.dedent(_SERVER))
