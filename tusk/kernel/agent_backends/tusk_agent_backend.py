from tusk.kernel.agent_backends.agent_backend import AgentBackend
from tusk.kernel.agent_backends.backend_run_logger import BackendRunLogger
from tusk.kernel.agent_backends.agent_request import AgentRequest
from tusk.kernel.agent_backends.agent_result import AgentResult
from tusk.kernel.interfaces.agent import Agent
from tusk.shared.logging.interfaces.log_printer import LogPrinter

__all__ = ["TuskAgentBackend"]


class TuskAgentBackend(AgentBackend):
    def __init__(self, agent: Agent, log_printer: LogPrinter | None = None) -> None:
        if agent is None:
            raise ValueError("agent cannot be None")
        self._agent = agent
        self._run_logger = BackendRunLogger(log_printer, self.name) if log_printer else None

    @property
    def name(self) -> str:
        return "tusk"

    @property
    def supports_streaming(self) -> bool:
        return False

    def run(self, request: AgentRequest) -> AgentResult:
        if request is None:
            raise ValueError("request cannot be None")
        started_at = self._start(request)
        try:
            result = self._result(request)
        except Exception as error:
            self._failure(request, started_at, error)
            raise
        self._end(request, started_at, result)
        return result

    def _result(self, request: AgentRequest) -> AgentResult:
        reply = self._agent.process_command(request.user_text)
        metadata = {**request.metadata, "backend": self.name, "mode": request.mode}
        return AgentResult(True, reply, request.session_id, metadata)

    def _start(self, request: AgentRequest) -> float:
        return self._run_logger.start(request) if self._run_logger else 0.0

    def _end(self, request: AgentRequest, started_at: float, result: AgentResult) -> None:
        if self._run_logger:
            self._run_logger.end(request, started_at, result)

    def _failure(self, request: AgentRequest, started_at: float, error: Exception) -> None:
        if self._run_logger:
            self._run_logger.failure(request, started_at, "failed", str(error))
