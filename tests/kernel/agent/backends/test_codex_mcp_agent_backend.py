import time
from types import SimpleNamespace
from unittest.mock import patch

from tusk.kernel.agent.backends.agent_request import AgentRequest
from tusk.kernel.agent.backends.codex_mcp_agent_backend import CodexMcpAgentBackend
from tests.recording_log_printer import RecordingLogPrinter

_CLIENT = "tusk.kernel.agent.backends.codex_mcp_agent_backend.Client"


class FakeClient:
    instances: list["FakeClient"] = []
    pending: list[object] = []

    def __init__(self, command: list[str], cwd: str, timeout_seconds: float) -> None:
        FakeClient.instances.append(self)
        self.command = command
        self.responses, FakeClient.pending = FakeClient.pending, []
        self.calls: list[tuple[str, dict]] = []
        self.delay = 0.0
        self.running = True

    def call_tool(self, name: str, arguments: dict) -> dict:
        self.calls.append((name, arguments))
        time.sleep(self.delay)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def is_running(self) -> bool:
        return self.running

    def stop(self) -> None:
        self.running = False


def backend() -> CodexMcpAgentBackend:
    FakeClient.instances = []
    config = SimpleNamespace(codex_exec_binary="codex", codex_exec_timeout_seconds=60, codex_exec_workdir="")
    return CodexMcpAgentBackend(config, RecordingLogPrinter())


def success(thread_id: str = "t-1") -> dict:
    return {"structuredContent": {"threadId": thread_id, "content": "done"}}


def test_first_turn_uses_codex_tool_with_built_prompt_and_returns_thread_id() -> None:
    instance = backend()
    with patch(_CLIENT, FakeClient):
        FakeClient.pending = [success("t-7")]
        result = instance.run(AgentRequest("open gedit", "command"))
    client = FakeClient.instances[0]
    assert client.command == ["codex", "mcp-server"]
    assert client.calls[0][0] == "codex"
    assert "## User command" in client.calls[0][1]["prompt"]
    assert "gnome MCP tools" in client.calls[0][1]["prompt"]
    assert result.session_id == "t-7"


def test_session_id_routes_to_codex_reply_on_same_client() -> None:
    instance = backend()
    with patch(_CLIENT, FakeClient):
        FakeClient.pending = [success()]
        instance.run(AgentRequest("open gedit", "command"))
        FakeClient.instances[0].responses = [success()]
        instance.run(AgentRequest("now close it", "command", "t-1"))
    assert len(FakeClient.instances) == 1
    assert FakeClient.instances[0].calls[1][0] == "codex-reply"
    assert FakeClient.instances[0].calls[1][1]["threadId"] == "t-1"


def test_missing_binary_returns_failed_result() -> None:
    instance = backend()
    with patch(_CLIENT, side_effect=FileNotFoundError("codex")):
        result = instance.run(AgentRequest("open gedit", "command"))
    assert result.handled is False
    assert "missing binary" in result.reply
    assert result.status == "failed"


def test_timeout_returns_timeout_status_and_respawns_on_next_run() -> None:
    instance = backend()
    with patch(_CLIENT, FakeClient):
        FakeClient.pending = [TimeoutError()]
        result = instance.run(AgentRequest("open gedit", "command"))
        FakeClient.pending = [success("t-2")]
        second = instance.run(AgentRequest("try again", "command"))
    assert result.status == "timeout"
    assert FakeClient.instances[0].running is False
    assert len(FakeClient.instances) == 2
    assert second.session_id == "t-2"


def test_failed_codex_reply_recovers_with_fresh_thread() -> None:
    instance = backend()
    with patch(_CLIENT, FakeClient):
        FakeClient.pending = [success()]
        instance.run(AgentRequest("open gedit", "command"))
        FakeClient.instances[0].responses = [RuntimeError("thread not found"), success("t-9")]
        result = instance.run(AgentRequest("now close it", "command", "t-1"))
    assert [name for name, _ in FakeClient.instances[0].calls] == ["codex", "codex-reply", "codex"]
    assert result.handled is True
    assert result.session_id == "t-9"


def test_runtime_error_without_session_fails_after_single_attempt() -> None:
    instance = backend()
    with patch(_CLIENT, FakeClient):
        FakeClient.pending = [RuntimeError("boom")]
        result = instance.run(AgentRequest("open gedit", "command"))
    assert result.handled is False
    assert result.status == "failed"
    assert len(FakeClient.instances[0].calls) == 1
