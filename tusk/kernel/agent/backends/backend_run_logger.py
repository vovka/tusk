import time

from tusk.kernel.agent.backends.agent_request import AgentRequest
from tusk.kernel.agent.backends.agent_result import AgentResult
from tusk.shared.logging.interfaces.log_printer import LogPrinter

__all__ = ["BackendRunLogger"]


class BackendRunLogger:
    def __init__(self, log_printer: LogPrinter, backend_name: str) -> None:
        self._log_printer = log_printer
        self._backend_name = backend_name

    def start(self, request: AgentRequest) -> float:
        started_at = time.monotonic()
        self._log(f"backend start backend={self._backend_name} {self._request_ref(request)}")
        return started_at

    def end(self, request: AgentRequest, started_at: float, result: AgentResult) -> None:
        elapsed = time.monotonic() - started_at
        summary = self._error_summary(result)
        code = self._exit_code(result)
        self._log(
            f"backend end backend={self._backend_name} {self._request_ref(request)} "
            f"duration={elapsed:.2f}s status={result.status}{code}{summary}"
        )

    def failure(self, request: AgentRequest, started_at: float, status: str, error: str) -> None:
        elapsed = time.monotonic() - started_at
        summary = self._safe_summary(error)
        self._log(
            f"backend end backend={self._backend_name} {self._request_ref(request)} "
            f"duration={elapsed:.2f}s status={status} error={summary}"
        )

    def schema(self, request: AgentRequest, success: bool, detail: str) -> None:
        outcome = "success" if success else "failure"
        self._log(
            f"schema parsing {outcome} backend={self._backend_name} "
            f"{self._request_ref(request)} detail={detail}"
        )

    def _request_ref(self, request: AgentRequest) -> str:
        metadata = request.metadata or {}
        request_id = metadata.get("request_id", "")
        if request.session_id:
            return f"session_id={request.session_id}"
        return f"request_id={request_id}" if request_id else "request_id=unknown"

    def _error_summary(self, result: AgentResult) -> str:
        if result.handled and result.status == "success":
            return ""
        return f" error={self._safe_summary(result.reply)}"

    def _exit_code(self, result: AgentResult) -> str:
        code = result.metadata.get("codex_exit_code") if result.metadata else None
        return f" codex_exit_code={code}" if code is not None else ""

    def _safe_summary(self, value: object) -> str:
        return str(value or "").replace("\n", " ")[:160]

    def _log(self, message: str) -> None:
        self._log_printer.log("agent_backend", message, "agent")
