import asyncio
import time

import pytest

from tusk.shared.mcp.mcp_client import MCPClient

_REPLY = (
    "import json, sys\n"
    "line = sys.stdin.readline()\n"
    "request = json.loads(line)\n"
    "sys.stdout.write(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'result': {}}) + '\\n')\n"
    "sys.stdout.flush()\n"
)
_HANGING = "import time\ntime.sleep(30)\n"
_GARBAGE = "print('this is not json', flush=True)\nimport time\ntime.sleep(30)\n"
_STUBBORN = "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\n" + _REPLY + "time.sleep(30)\n"
_NOISY = "import sys\nsys.stderr.write('x' * 1048576)\nsys.stderr.flush()\n" + _REPLY
_CRASHING = "import sys\nsys.stderr.write('boom diagnostics')\nsys.exit(1)\n"


def test_request_times_out_when_server_hangs() -> None:
    client = MCPClient(response_timeout_seconds=0.5)
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="timed out"):
        asyncio.run(client.connect_stdio(["python", "-c", _HANGING], cwd="."))
    assert time.monotonic() - started < 5.0
    asyncio.run(client.shutdown())


def test_request_raises_runtime_error_on_malformed_response() -> None:
    client = MCPClient(response_timeout_seconds=2.0)
    with pytest.raises(RuntimeError, match="initialize"):
        asyncio.run(client.connect_stdio(["python", "-c", _GARBAGE], cwd="."))
    asyncio.run(client.shutdown())


def test_shutdown_kills_server_that_ignores_sigterm() -> None:
    client = MCPClient(response_timeout_seconds=2.0)
    asyncio.run(client.connect_stdio(["python", "-c", _STUBBORN], cwd="."))
    started = time.monotonic()
    asyncio.run(client.shutdown())
    assert time.monotonic() - started < 5.0
    assert client.is_running() is False


def test_large_stderr_output_does_not_deadlock_requests() -> None:
    client = MCPClient(response_timeout_seconds=5.0)
    asyncio.run(client.connect_stdio(["python", "-c", _NOISY], cwd="."))
    asyncio.run(client.shutdown())


def test_error_message_includes_server_stderr() -> None:
    client = MCPClient(response_timeout_seconds=2.0)
    with pytest.raises(RuntimeError, match="boom diagnostics"):
        asyncio.run(client.connect_stdio(["python", "-c", _CRASHING], cwd="."))
    asyncio.run(client.shutdown())
