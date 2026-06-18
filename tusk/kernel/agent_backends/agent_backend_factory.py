from tusk.kernel.agent_backends.agent_backend import AgentBackend
from tusk.kernel.agent_backends.codex_exec_agent_backend import CodexExecAgentBackend
from tusk.kernel.agent_backends.tusk_agent_backend import TuskAgentBackend
from tusk.kernel.interfaces.agent import Agent
from tusk.shared.logging.interfaces.log_printer import LogPrinter

__all__ = ["AgentBackendFactory"]


class AgentBackendFactory:
    def __init__(self, agent: Agent, config: object, log_printer: LogPrinter) -> None:
        if agent is None:
            raise ValueError("agent cannot be None")
        if config is None:
            raise ValueError("config cannot be None")
        if log_printer is None:
            raise ValueError("log_printer cannot be None")
        self._agent = agent
        self._config = config
        self._log_printer = log_printer

    def create(self) -> AgentBackend:
        backend_name = self._backend_name()
        if backend_name == "tusk":
            return self._selected(TuskAgentBackend(self._agent))
        if backend_name == "codex_exec":
            return self._selected(CodexExecAgentBackend(self._config, self._log_printer))
        raise ValueError(f"Unknown agent backend '{backend_name}'")

    def _backend_name(self) -> str:
        return str(getattr(self._config, "agent_backend", "tusk"))

    def _selected(self, backend: AgentBackend) -> AgentBackend:
        message = f"Selected agent backend: {backend.name}"
        self._log_printer.log("agent_backend", message, "agent")
        return backend
