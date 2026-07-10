from tusk.kernel.agent.backends import AgentBackend, AgentRequest
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["CommandMode"]


class CommandMode:
    def __init__(self, agent_backend: AgentBackend, log_printer: LogPrinter) -> None:
        self._agent_backend = agent_backend
        self._log = log_printer
        self._session_id = ""

    def process_command(self, command: str, kind: str = "conversation") -> KernelResponse:
        result = self._agent_backend.run(self._request(command, kind))
        self._session_id = result.session_id
        return KernelResponse(result.handled, result.reply)

    def _request(self, command: str, kind: str) -> AgentRequest:
        return AgentRequest(command, kind, self._session_id)
