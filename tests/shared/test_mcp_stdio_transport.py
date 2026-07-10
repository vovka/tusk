import threading
import time

from tusk.shared.mcp.mcp_stdio_transport import MCPStdioTransport

_HANGING = ["python", "-c", "import time; time.sleep(30)"]
_EMIT_THEN_HANG = ["python", "-c", "import sys, time\nsys.stdout.write('late\\n')\nsys.stdout.flush()\ntime.sleep(30)\n"]


def test_read_line_timeouts_do_not_leak_threads() -> None:
    transport = MCPStdioTransport(_HANGING, cwd=".", env=None, response_timeout_seconds=0.05)
    before = threading.active_count()
    for _ in range(5):
        assert transport.read_line() is None
    assert threading.active_count() <= before
    transport.stop()


def test_write_discards_stale_reply_before_next_request() -> None:
    transport = MCPStdioTransport(_EMIT_THEN_HANG, cwd=".", env=None, response_timeout_seconds=0.2)
    deadline = time.monotonic() + 5.0
    while transport._stdout_queue.empty() and time.monotonic() < deadline:
        time.sleep(0.01)
    transport.write_line("request")
    assert transport.read_line() is None
    transport.stop()
