import pytest

from tusk.kernel.agent_backends.agent_backend_factory import AgentBackendFactory
from tusk.kernel.agent_backends.codex_exec_agent_backend import CodexExecAgentBackend
from tusk.kernel.agent_backends.tusk_agent_backend import TuskAgentBackend


class RecordingAgent:
    def process_command(self, command: str) -> str:
        return command


class RecordingLogPrinter:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, str | None]] = []

    def log(self, tag: str, message: str, group: str | None = None) -> None:
        self.messages.append((tag, message, group))

    def show_wait(self, label: str, group: str = "wait") -> None:
        pass

    def clear_wait(self) -> None:
        pass


class BackendConfig:
    def __init__(self, agent_backend: str) -> None:
        self.agent_backend = agent_backend


def factory(agent_backend: str) -> tuple[AgentBackendFactory, RecordingLogPrinter]:
    log_printer = RecordingLogPrinter()
    instance = AgentBackendFactory(RecordingAgent(), BackendConfig(agent_backend), log_printer)
    return instance, log_printer


def test_agent_backend_factory_selects_tusk_backend() -> None:
    instance, _ = factory("tusk")
    assert isinstance(instance.create(), TuskAgentBackend)


def test_agent_backend_factory_selects_codex_exec_backend() -> None:
    instance, _ = factory("codex_exec")
    assert isinstance(instance.create(), CodexExecAgentBackend)


def test_agent_backend_factory_rejects_unknown_backend() -> None:
    instance, _ = factory("bogus")
    with pytest.raises(ValueError, match="Unknown agent backend 'bogus'"):
        instance.create()


def test_agent_backend_factory_logs_selected_backend() -> None:
    instance, log_printer = factory("tusk")
    instance.create()
    assert log_printer.messages == [("agent_backend", "Selected agent backend: tusk", "agent")]
