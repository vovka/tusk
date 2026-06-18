from tusk.kernel.agent_backends.agent_backend import AgentBackend
from tusk.kernel.agent_backends.agent_request import AgentRequest
from tusk.kernel.agent_backends.agent_result import AgentResult
from tusk.shared.logging.interfaces.log_printer import LogPrinter

__all__ = ["CodexExecAgentBackend"]


class CodexExecAgentBackend(AgentBackend):
    def __init__(self, config: object, log_printer: LogPrinter) -> None:
        if config is None:
            raise ValueError("config cannot be None")
        if log_printer is None:
            raise ValueError("log_printer cannot be None")
        self._config = config
        self._log_printer = log_printer

    @property
    def name(self) -> str:
        return "codex_exec"

    @property
    def supports_streaming(self) -> bool:
        return False

    def run(self, request: AgentRequest) -> AgentResult:
        raise NotImplementedError("codex_exec backend execution is not implemented yet")
