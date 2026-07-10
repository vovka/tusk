import json
import subprocess
from types import SimpleNamespace

import pytest

from tests.recording_agent import RecordingAgent
from tests.recording_log_printer import RecordingLogPrinter
from tusk.kernel.agent.backends.agent_request import AgentRequest
from tusk.kernel.agent.backends.codex_exec_agent_backend import CodexExecAgentBackend
from tusk.kernel.agent.backends.tusk_agent_backend import TuskAgentBackend


def config() -> SimpleNamespace:
    return SimpleNamespace(
        codex_exec_binary="codex", codex_exec_model="", codex_exec_timeout_seconds=60,
        codex_exec_workdir="", codex_exec_sandbox_mode="read-only", codex_exec_extra_args=(),
        codex_exec_output_schema_path="/tmp/schema.json", codex_exec_log_raw_events=False,
    )


def request(**overrides: object) -> AgentRequest:
    return AgentRequest("secret prompt", "command", **overrides)


def completed(stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(["codex"], 0, stdout or _stream('{"reply":"Done."}'), "")


def _stream(payload: str) -> str:
    agent = {"type": "item.completed", "item": {"type": "agent_message", "text": payload}}
    return json.dumps(agent)


def run_broken_tusk_backend(log_printer: RecordingLogPrinter) -> None:
    class BrokenAgent:
        def process_command(self, command: str, kind: str = "conversation") -> str:
            raise RuntimeError("boom")

    request = AgentRequest("open", "command", metadata={"request_id": "req-1"})
    TuskAgentBackend(BrokenAgent(), log_printer).run(request)


def test_codex_exec_backend_logs_success_lifecycle(monkeypatch) -> None:
    log_printer = RecordingLogPrinter()
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed())
    CodexExecAgentBackend(config(), log_printer).run(request(session_id="session-1"))
    messages = [message for _, message, _ in log_printer.messages]
    assert any("backend start backend=codex_exec session_id=session-1" in message for message in messages)
    assert any("schema parsing success backend=codex_exec session_id=session-1" in message for message in messages)
    assert any("backend end backend=codex_exec session_id=session-1" in message for message in messages)
    assert any("status=success" in message and "duration=" in message for message in messages)
    assert all("secret prompt" not in message and "Done." not in message for message in messages)


def test_codex_exec_backend_logs_failure_lifecycle_with_exit_code(monkeypatch) -> None:
    log_printer = RecordingLogPrinter()
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(["codex"], 7, "raw", "bad"))
    CodexExecAgentBackend(config(), log_printer).run(request(metadata={"request_id": "request-1"}))
    messages = [message for _, message, _ in log_printer.messages]
    assert any("backend start backend=codex_exec request_id=request-1" in message for message in messages)
    assert any("backend end backend=codex_exec request_id=request-1" in message for message in messages)
    assert any("status=failed" in message and "codex_exit_code=7" in message for message in messages)
    assert all("raw" not in message for message in messages)


def test_codex_exec_backend_logs_schema_failure(monkeypatch) -> None:
    log_printer = RecordingLogPrinter()
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed("not-json"))
    CodexExecAgentBackend(config(), log_printer).run(request(session_id="session-2"))
    messages = [message for _, message, _ in log_printer.messages]
    assert any("schema parsing failure backend=codex_exec session_id=session-2" in message for message in messages)


def test_codex_exec_backend_handles_none_metadata(monkeypatch) -> None:
    log_printer = RecordingLogPrinter()
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed())
    result = CodexExecAgentBackend(config(), log_printer).run(request(metadata=None))
    messages = [message for _, message, _ in log_printer.messages]
    assert result.metadata["backend"] == "codex_exec"
    assert any("request_id=unknown" in message for message in messages)


def test_tusk_agent_backend_logs_success_lifecycle() -> None:
    log_printer = RecordingLogPrinter()
    TuskAgentBackend(RecordingAgent(), log_printer).run(AgentRequest("open browser", "command", "session-1"))
    messages = [message for _, message, _ in log_printer.messages]
    assert messages[0] == "backend start backend=tusk session_id=session-1"
    assert "backend end backend=tusk session_id=session-1" in messages[1]
    assert "status=success" in messages[1]
    assert "duration=" in messages[1]
    assert "open browser" not in " ".join(messages)


def test_tusk_agent_backend_logs_failure_lifecycle() -> None:
    log_printer = RecordingLogPrinter()
    with pytest.raises(RuntimeError, match="boom"):
        run_broken_tusk_backend(log_printer)
    messages = [message for _, message, _ in log_printer.messages]
    assert messages[0] == "backend start backend=tusk request_id=req-1"
    assert "backend end backend=tusk request_id=req-1" in messages[1]
    assert "status=failed" in messages[1]
    assert "error=boom" in messages[1]
