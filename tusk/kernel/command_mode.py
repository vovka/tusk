from tusk.kernel.agent_backends import AgentBackend, AgentRequest
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["CommandMode"]


class CommandMode:
    def __init__(self, agent_backend: AgentBackend, log_printer: LogPrinter) -> None:
        self._agent_backend = agent_backend
        self._log = log_printer

    def process_command(self, command: str) -> KernelResponse:
        result = self._agent_backend.run(AgentRequest(user_text=command, mode="command"))
        return KernelResponse(result.handled, result.reply)
