import json
import time

import pytest

from tusk.kernel.agent.backends.codex_mcp.client import Client

# Fake codex mcp-server: rejects initialize without clientInfo, echoes the
# methods it has seen inside the tools/call result, and emits two codex/event
# notification lines before each tools/call response.
_SERVER = """
import json, sys
seen = []
for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    seen.append(method)
    if "id" not in message:
        continue
    if method == "initialize" and "clientInfo" not in message.get("params", {}):
        error = {"code": -32601, "message": "method not found: initialize"}
        response = {"jsonrpc": "2.0", "id": message["id"], "error": error}
    elif method == "tools/call":
        for _ in range(2):
            event = {"jsonrpc": "2.0", "method": "codex/event", "params": {}}
            sys.stdout.write(json.dumps(event) + "\\n")
        result = {"structuredContent": {"threadId": "t-1", "content": json.dumps(seen)}}
        response = {"jsonrpc": "2.0", "id": message["id"], "result": result}
    else:
        response = {"jsonrpc": "2.0", "id": message["id"], "result": {}}
    sys.stdout.write(json.dumps(response) + "\\n")
    sys.stdout.flush()
"""

_HANGING = "import time\ntime.sleep(30)\n"
_CRASHING = "import sys\nsys.stderr.write('boom diagnostics')\nsys.exit(1)\n"
_ERROR = """
import json, sys
for line in sys.stdin:
    message = json.loads(line)
    if "id" not in message:
        continue
    if message.get("method") == "tools/call":
        error = {"code": -1, "message": "codex blew up"}
        response = {"jsonrpc": "2.0", "id": message["id"], "error": error}
    else:
        response = {"jsonrpc": "2.0", "id": message["id"], "result": {}}
    sys.stdout.write(json.dumps(response) + "\\n")
    sys.stdout.flush()
"""


def client(script: str, timeout: float = 5.0) -> Client:
    return Client(["python", "-c", script], cwd=".", timeout_seconds=timeout)


def test_client_handshakes_with_client_info_and_initialized_notification() -> None:
    instance = client(_SERVER)
    payload = instance.call_tool("codex", {"prompt": "hi"})
    seen = json.loads(payload["structuredContent"]["content"])
    assert "notifications/initialized" in seen
    instance.stop()


def test_client_returns_result_despite_interleaved_notifications() -> None:
    instance = client(_SERVER)
    payload = instance.call_tool("codex", {"prompt": "hi"})
    assert payload["structuredContent"]["threadId"] == "t-1"
    instance.stop()


def test_client_raises_timeout_error_when_server_hangs() -> None:
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        client(_HANGING, timeout=0.5)
    assert time.monotonic() - started < 5.0


def test_client_raises_runtime_error_with_stderr_when_server_crashes() -> None:
    with pytest.raises(RuntimeError, match="boom diagnostics"):
        client(_CRASHING)


def test_client_raises_runtime_error_on_error_response() -> None:
    instance = client(_ERROR)
    with pytest.raises(RuntimeError, match="codex blew up"):
        instance.call_tool("codex", {"prompt": "hi"})
    instance.stop()


def test_client_raises_file_not_found_for_missing_binary() -> None:
    with pytest.raises(FileNotFoundError):
        Client(["missing-codex-binary", "mcp-server"], cwd=".", timeout_seconds=1.0)


def test_client_stop_terminates_server() -> None:
    instance = client(_SERVER)
    instance.stop()
    assert instance.is_running() is False
