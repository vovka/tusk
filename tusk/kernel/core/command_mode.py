from tusk.kernel.agent.backends import AgentBackend, AgentRequest
from tusk.kernel.interfaces.action_confirmation import ActionConfirmation
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["CommandMode"]


class CommandMode:
    def __init__(self, agent_backend: AgentBackend, log_printer: LogPrinter, confirmation: ActionConfirmation) -> None:
        self._agent_backend = agent_backend
        self._log = log_printer
        self._confirmation = confirmation
        self._session_id = ""

    def process_command(self, command: str, kind: str = "conversation") -> KernelResponse:
        resolved = self._confirmation.resolve(command)
        if resolved is not None:
            return resolved
        response = self._run_backend(command, kind)
        question = self._confirmation.take_question()
        # the spoken question must win over whatever the agent said, so the user knows a yes is expected
        return KernelResponse(True, question) if question else response

    def _run_backend(self, command: str, kind: str) -> KernelResponse:
        result = self._agent_backend.run(self._request(command, kind))
        if kind != "command":
            self._session_id = result.session_id
        return KernelResponse(result.handled, result.reply)

    def _request(self, command: str, kind: str) -> AgentRequest:
        # commands are one-shot: a transient session keeps them off the shared conversation thread
        session_id = "" if kind == "command" else self._session_id
        return AgentRequest(command, kind, session_id)
