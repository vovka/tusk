import types

from tusk.kernel.agent.confirmation.confirming_command_mode import ConfirmingCommandMode
from tusk.shared.schemas.kernel_response import KernelResponse


class _Gate:
    def __init__(self, resolved: KernelResponse | None, question: str | None) -> None:
        self._resolved, self._question = resolved, question

    def resolve(self, text: str) -> KernelResponse | None:
        return self._resolved

    def take_question(self) -> str | None:
        return self._question


def _inner(seen: list[str]) -> object:
    return types.SimpleNamespace(process_command=lambda text, kind: seen.append(text) or KernelResponse(True, "agent"))


def test_confirmation_reply_skips_agent() -> None:
    seen: list[str] = []
    mode = ConfirmingCommandMode(_inner(seen), _Gate(KernelResponse(True, "Done."), None))
    assert mode.process_command("yes", "command").reply == "Done."
    assert seen == []


def test_new_question_replaces_agent_reply() -> None:
    seen: list[str] = []
    mode = ConfirmingCommandMode(_inner(seen), _Gate(None, "Close window 'X'? Say 'Tusk, yes' to confirm."))
    assert mode.process_command("close X", "command").reply == "Close window 'X'? Say 'Tusk, yes' to confirm."
    assert seen == ["close X"]


def test_plain_command_passes_through() -> None:
    mode = ConfirmingCommandMode(_inner([]), _Gate(None, None))
    assert mode.process_command("hi", "conversation").reply == "agent"
