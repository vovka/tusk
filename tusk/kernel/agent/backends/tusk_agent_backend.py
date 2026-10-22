from tusk.kernel.agent.backends.agent_backend import AgentBackend
from tusk.kernel.agent.backends.backend_request import BackendRequest
from tusk.kernel.agent.backends.backend_result import BackendResult
from tusk.kernel.agent.backends.backend_run_logger import BackendRunLogger
from tusk.kernel.core.main_agent import MainAgent
from tusk.shared.interfaces.log_printer import LogPrinter

__all__ = ["TuskAgentBackend"]


class TuskAgentBackend(AgentBackend):
    def __init__(self, agent: MainAgent, log_printer: LogPrinter | None = None) -> None:
        if agent is None:
            raise ValueError("agent cannot be None")
        self._agent = agent
        self._run_logger = BackendRunLogger(log_printer, self.name) if log_printer else None

    @property
    def name(self) -> str:
        return "tusk"

    def run(self, request: BackendRequest) -> BackendResult:
        if request is None: raise ValueError("request cannot be None")
        started_at = self._run_logger.start(request) if self._run_logger else None
        try:
            result = self._result(request)
        except Exception as error:
            if self._run_logger and started_at is not None:
                self._run_logger.failure(request, started_at, "failed", str(error))
            raise
        if self._run_logger and started_at is not None: self._run_logger.end(request, started_at, result)
        return result

    def _result(self, request: BackendRequest) -> BackendResult:
        reply = self._agent.process_command(request.user_text, request.mode)
        metadata = {**(request.metadata or {}), "backend": self.name, "mode": request.mode}
        return BackendResult(True, reply, request.session_id, metadata)
