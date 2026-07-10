from unittest.mock import Mock

import pytest

from tests.backend_config import BackendConfig
from tests.recording_agent import RecordingAgent
from tests.recording_log_printer import RecordingLogPrinter
from tusk.kernel.agent_backends.agent_backend_factory import AgentBackendFactory
from tusk.kernel.agent_backends.agent_request import AgentRequest
from tusk.kernel.agent_backends.agent_result import AgentResult
from tusk.kernel.agent_backends.codex_exec_agent_backend import CodexExecAgentBackend
from tusk.kernel.agent_backends.codex_mcp_agent_backend import CodexMcpAgentBackend
from tusk.kernel.agent_backends.fallback_agent_backend import FallbackAgentBackend
from tusk.kernel.agent_backends.tusk_agent_backend import TuskAgentBackend


def factory(agent_backend: str, fallback: str = "") -> tuple[AgentBackendFactory, RecordingLogPrinter]:
    log_printer = RecordingLogPrinter()
    config = BackendConfig(agent_backend, fallback)
    return AgentBackendFactory(RecordingAgent(), config, log_printer), log_printer


def test_agent_backend_factory_selects_tusk_backend() -> None:
    instance, _ = factory("tusk")
    assert isinstance(instance.create(), TuskAgentBackend)


def test_agent_backend_factory_selects_codex_exec_backend() -> None:
    instance, _ = factory("codex_exec")
    assert isinstance(instance.create(), CodexExecAgentBackend)


def test_agent_backend_factory_wraps_codex_exec_when_fallback_enabled() -> None:
    instance, _ = factory("codex_exec", "tusk")
    assert isinstance(instance.create(), FallbackAgentBackend)


def test_agent_backend_factory_does_not_wrap_codex_exec_when_fallback_disabled() -> None:
    instance, _ = factory("codex_exec", "")
    assert not isinstance(instance.create(), FallbackAgentBackend)


def test_agent_backend_factory_selects_codex_mcp_backend() -> None:
    instance, _ = factory("codex_mcp")
    assert isinstance(instance.create(), CodexMcpAgentBackend)


def test_agent_backend_factory_wraps_codex_mcp_when_fallback_enabled() -> None:
    instance, _ = factory("codex_mcp", "tusk")
    assert isinstance(instance.create(), FallbackAgentBackend)


def test_agent_backend_factory_does_not_wrap_codex_mcp_when_fallback_disabled() -> None:
    instance, _ = factory("codex_mcp", "")
    assert not isinstance(instance.create(), FallbackAgentBackend)


def test_agent_backend_factory_rejects_unknown_backend() -> None:
    instance, _ = factory("bogus")
    with pytest.raises(ValueError, match="Unknown agent backend 'bogus'"):
        instance.create()


def test_agent_backend_factory_logs_selected_backend() -> None:
    instance, log_printer = factory("tusk")
    instance.create()
    assert log_printer.messages == [("agent_backend", "Selected agent backend: tusk", "agent")]


def test_fallback_backend_runs_tusk_after_codex_failed_result() -> None:
    codex = Mock()
    tusk = Mock()
    codex.run.return_value = AgentResult(False, "bad", metadata={"backend": "codex_exec"})
    tusk.run.return_value = AgentResult(True, "ok", metadata={"backend": "tusk"})
    result = FallbackAgentBackend(codex, tusk).run(AgentRequest("prompt", "command"))
    assert result.handled == tusk.run.return_value.handled
    assert result.reply == tusk.run.return_value.reply
    assert result.status == tusk.run.return_value.status
    assert result.metadata["codex_exec_failure"]["reply"] == "bad"


def test_fallback_backend_handles_missing_tusk_metadata() -> None:
    codex = Mock()
    tusk = Mock()
    codex.run.return_value = AgentResult(False, "bad", metadata={"backend": "codex_exec"})
    tusk.run.return_value = AgentResult(True, "ok", metadata=None)  # type: ignore[arg-type]
    result = FallbackAgentBackend(codex, tusk).run(AgentRequest("prompt", "command"))
    assert result.metadata["codex_exec_failure"]["status"] == "failed"
    assert result.metadata["codex_exec_failure"]["reply"] == "bad"


def test_fallback_backend_does_not_run_tusk_after_codex_timeout() -> None:
    codex = Mock()
    tusk = Mock()
    codex.run.return_value = AgentResult(False, "slow", status="timeout")
    result = FallbackAgentBackend(codex, tusk).run(AgentRequest("prompt", "command"))
    tusk.run.assert_not_called()
    assert result is codex.run.return_value


def test_fallback_backend_does_not_run_tusk_after_codex_cancelled() -> None:
    codex = Mock()
    tusk = Mock()
    codex.run.return_value = AgentResult(False, "stop", status="cancelled")
    result = FallbackAgentBackend(codex, tusk).run(AgentRequest("prompt", "command"))
    tusk.run.assert_not_called()
    assert result is codex.run.return_value
