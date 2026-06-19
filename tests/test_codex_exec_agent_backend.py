import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

from tusk.kernel.agent_backends.agent_request import AgentRequest
from tusk.kernel.agent_backends.codex_exec_agent_backend import CodexExecAgentBackend


def config(**overrides: object) -> SimpleNamespace:
    values = {
        "codex_exec_binary": "codex", "codex_exec_model": "",
        "codex_exec_timeout_seconds": 60, "codex_exec_workdir": "",
        "codex_exec_sandbox_mode": "read-only", "codex_exec_extra_args": (),
        "codex_exec_output_schema_path": "/tmp/schema.json", "codex_exec_log_raw_events": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def backend(**overrides: object) -> CodexExecAgentBackend:
    return CodexExecAgentBackend(config(**overrides), Mock())


def completed(command: list[str], stdout: str = '{"reply":"Done."}') -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(command, 0, stdout, "")


def request(**overrides: object) -> AgentRequest:
    return AgentRequest("secret prompt", "command", **overrides)


def test_codex_exec_backend_builds_command(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: calls.append(kwargs) or completed(args[0]))
    result = backend(codex_exec_model="gpt-5.5", codex_exec_extra_args="--foo 'bar baz'").run(request())
    assert calls[0]["cwd"] is None
    assert calls[0]["timeout"] == 60
    assert result.reply == "Done."


def test_codex_exec_backend_command_includes_flags(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: calls.append(args[0]) or completed(args[0]))
    backend(codex_exec_model="gpt-5.5", codex_exec_extra_args="--foo 'bar baz'").run(request())
    assert calls[0] == [
        "codex", "exec", "--json", "--output-schema", "/tmp/schema.json", "--model", "gpt-5.5",
        "--sandbox", "read-only", "--foo", "bar baz", "secret prompt",
    ]


def test_codex_exec_backend_uses_request_overrides(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: calls.append(kwargs) or completed(args[0]))
    backend().run(request(working_directory="/tmp/work", timeout_seconds=3, environment={"A": "B"}))
    assert calls[0]["cwd"] == "/tmp/work"
    assert calls[0]["timeout"] == 3
    assert calls[0]["env"]["A"] == "B"


def test_codex_exec_backend_handles_none_environment(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: calls.append(kwargs) or completed(args[0]))
    backend().run(request(environment=None))
    assert isinstance(calls[0]["env"], dict)


def test_codex_exec_backend_preserves_zero_timeout(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: calls.append(kwargs) or completed(args[0]))
    backend().run(request(timeout_seconds=0))
    assert calls[0]["timeout"] == 0


def test_codex_exec_backend_uses_config_defaults_and_parsed_status(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: completed(command, '{"status":"failed","reply":"No"}'))
    result = backend(codex_exec_workdir="/tmp/default", codex_exec_sandbox_mode="", codex_exec_extra_args=None).run(
        AgentRequest("prompt", "command")
    )
    assert result.status == "failed"
    assert result.metadata["backend"] == "codex_exec"


def test_codex_exec_backend_handles_process_failures(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=FileNotFoundError("codex")))
    result = backend().run(AgentRequest("prompt", "command"))
    assert result.status == "failed"
    assert "missing binary" in result.reply


def test_codex_exec_backend_handles_timeout(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=subprocess.TimeoutExpired("codex", 1)))
    result = backend().run(AgentRequest("prompt", "command"))
    assert result.status == "timeout"
    assert result.handled is False


def test_codex_exec_backend_handles_nonzero(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(["codex"], 7, "", "bad"))
    result = backend().run(AgentRequest("prompt", "command"))
    assert result.status == "failed"
    assert "exit code 7" in result.reply


def test_codex_exec_backend_handles_invalid_json(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed(["codex"], "not-json"))
    result = backend().run(AgentRequest("prompt", "command"))
    assert result.status == "failed"
    assert "Invalid JSON" in result.reply

