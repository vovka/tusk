from collections.abc import Callable

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.interfaces.gatekeeper import Gatekeeper
from tusk.shared.schemas.utterance import Utterance

__all__ = ["DictationGatekeeper"]


class DictationGatekeeper(Gatekeeper):
    def __init__(self, dictation_gate: object, stop_callback: Callable[[], None], log: object) -> None:
        self._gate = dictation_gate
        self._stop = stop_callback
        self._log = log

    def evaluate(self, utterance: Utterance, recent: list[Utterance]) -> object:
        return None

    def process(
        self,
        utterance: Utterance | BufferedUtterance,
        recent: list[Utterance],
        candidates: list[BufferedUtterance] | None = None,
    ) -> GateDispatch:
        text = utterance.text
        if self._gate.should_stop(text):
            self._stop()
            return GateDispatch("drop")
        return GateDispatch("forward_current", text)
