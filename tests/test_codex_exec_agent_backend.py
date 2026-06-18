import json
import subprocess
from dataclasses import dataclass

from tusk.kernel.agent_backends.agent_request import AgentRequest
from tusk.kernel.agent_backends.codex_exec_agent_backend import CodexExecAgentBackend


@dataclass(frozen=True)
class CodexConfig:
    codex_exec_binary: str = "codex"
    codex_exec_model: str = ""
    codex_exec_timeout_seconds: int = 60
    codex_exec_workdir: str = ""
    codex_exec_sandbox_mode: str = "read-only"
    codex_exec_extra_args: object = ()
    codex_exec_output_schema_path: str = "/tmp/schema.json"
    codex_exec_log_raw_events: bool = False


class RecordingLogPrinter:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def log(self, tag: str, message: str, group: str | None = None) -> None:
        self.messages.append(message)

    def show_wait(self, label: str, group: str = "wait") -> None:
        pass

    def clear_wait(self) -> None:
        pass


def test_codex_exec_backend_runs_command_with_request_overrides(monkeypatch) -> None:
    calls = []

    def fake_run(command, cwd, timeout, env, capture_output, text):
        calls.append((command, cwd, timeout, env, capture_output, text))
        return subprocess.CompletedProcess(command, 0, json.dumps({"reply": "Done."}), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    config = CodexConfig(codex_exec_model="gpt-5.5", codex_exec_extra_args="--foo 'bar baz'")
    request = AgentRequest(
        "secret prompt", "command", working_directory="/tmp/work", timeout_seconds=3, environment={"A": "B"}
    )
    result = CodexExecAgentBackend(config, RecordingLogPrinter()).run(request)
    assert calls[0][0] == [
        "codex", "exec", "--json", "--output-schema", "/tmp/schema.json", "--model", "gpt-5.5",
        "--sandbox", "read-only", "--foo", "bar baz", "secret prompt",
    ]
    assert calls[0][1] == "/tmp/work"
    assert calls[0][2] == 3
    assert calls[0][3]["A"] == "B"
    assert calls[0][4:] == (True, True)
    assert result.status == "success"
    assert result.reply == "Done."


def test_codex_exec_backend_uses_config_defaults_and_parsed_status(monkeypatch) -> None:
    def fake_run(command, cwd, timeout, env, capture_output, text):
        assert "--model" not in command
        return subprocess.CompletedProcess(command, 0, '{"status":"failed","reply":"No"}', "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    config = CodexConfig(codex_exec_workdir="/tmp/default", codex_exec_sandbox_mode="")
    result = CodexExecAgentBackend(config, RecordingLogPrinter()).run(
        AgentRequest("prompt", "command")
    )
    assert result.status == "failed"
    assert result.handled is False
    assert result.metadata["backend"] == "codex_exec"


def test_codex_exec_backend_handles_process_failures(monkeypatch) -> None:
    def missing(*args, **kwargs):
        raise FileNotFoundError("codex")

    monkeypatch.setattr(subprocess, "run", missing)
    result = CodexExecAgentBackend(CodexConfig(), RecordingLogPrinter()).run(
        AgentRequest("prompt", "command")
    )
    assert result.status == "failed"
    assert "missing binary" in result.reply


def test_codex_exec_backend_handles_timeout(monkeypatch) -> None:
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("codex", 1)

    monkeypatch.setattr(subprocess, "run", timeout)
    result = CodexExecAgentBackend(CodexConfig(), RecordingLogPrinter()).run(
        AgentRequest("prompt", "command")
    )
    assert result.status == "timeout"
    assert result.handled is False


def test_codex_exec_backend_handles_nonzero_and_invalid_json(monkeypatch) -> None:
    def nonzero(*args, **kwargs):
        return subprocess.CompletedProcess(["codex"], 7, "", "bad stderr")

    monkeypatch.setattr(subprocess, "run", nonzero)
    result = CodexExecAgentBackend(CodexConfig(), RecordingLogPrinter()).run(
        AgentRequest("prompt", "command")
    )
    assert result.status == "failed"
    assert "exit code 7" in result.reply

    def invalid(*args, **kwargs):
        return subprocess.CompletedProcess(["codex"], 0, "not-json", "")

    monkeypatch.setattr(subprocess, "run", invalid)
    result = CodexExecAgentBackend(CodexConfig(), RecordingLogPrinter()).run(
        AgentRequest("prompt", "command")
    )
    assert result.status == "failed"
    assert "Invalid JSON" in result.reply
