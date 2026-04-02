from tusk.kernel.interfaces.agent import Agent
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["CommandMode"]


class CommandMode:
    def __init__(self, agent: Agent, log_printer: LogPrinter) -> None:
        self._agent = agent
        self._log = log_printer

    def process_command(self, command: str) -> KernelResponse:
        reply = self._agent.process_command(command)
        return KernelResponse(True, reply)
