from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_action import GateAction
from tusk.shared.schemas.voice.gate_dispatch import GateDispatch
from shells.voice.interfaces.gatekeeper import Gatekeeper
from shells.voice.speech.confirmation_reply import ConfirmationReply
from tusk.shared.schemas.voice.utterance import Utterance

__all__ = ["ConfirmationAnswerGate"]


class ConfirmationAnswerGate(Gatekeeper):
    """Forwards a yes/no to a pending confirmation without asking the gatekeeper LLM, which calls it ambient."""

    def __init__(self, inner: Gatekeeper, reply: ConfirmationReply) -> None:
        self._inner = inner
        self._reply = reply

    def process(self, utterance: BufferedUtterance, recent: list[Utterance], candidates: list[BufferedUtterance]) -> GateDispatch:
        answer = self._reply.answer(utterance.text)
        if answer is None:
            return self._inner.process(utterance, recent, candidates)
        return GateDispatch(GateAction.FORWARD_CURRENT, answer, kind="command")
