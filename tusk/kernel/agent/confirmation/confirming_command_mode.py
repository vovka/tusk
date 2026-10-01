from tusk.kernel.interfaces.action_confirmation import ActionConfirmation
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["ConfirmingCommandMode"]


class ConfirmingCommandMode:
    def __init__(self, command_mode: object, confirmation: ActionConfirmation) -> None:
        self._command_mode = command_mode
        self._confirmation = confirmation

    def process_command(self, command: str, kind: str = "conversation") -> KernelResponse:
        resolved = self._confirmation.resolve(command)
        if resolved is not None:
            return resolved
        response = self._command_mode.process_command(command, kind)
        question = self._confirmation.take_question()
        # the spoken question must win over whatever the agent said, so the user knows a yes is expected
        return KernelResponse(True, question) if question else response
