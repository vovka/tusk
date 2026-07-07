from collections.abc import Callable

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.interfaces.gatekeeper import Gatekeeper
from tusk.shared.schemas.utterance import Utterance

__all__ = ["PlaybackGate"]


class PlaybackGate(Gatekeeper):
    """While TUSK speaks, allow only interrupt-or-drop so forward-all modes never type TUSK's own voice."""

    def __init__(
        self,
        inner: Gatekeeper,
        current_speech_text: Callable[[], str | None],
        stop_gate: object,
    ) -> None:
        self._inner = inner
        self._current_speech_text = current_speech_text
        self._stop_gate = stop_gate

    def process(
        self,
        utterance: Utterance | BufferedUtterance,
        recent: list[Utterance],
        candidates: list[BufferedUtterance] | None = None,
    ) -> GateDispatch:
        speaking = self._current_speech_text()
        if speaking is None:
            return self._inner.process(utterance, recent, candidates)
        text = utterance.text if isinstance(utterance, Utterance) else utterance.utterance.text
        return self._interrupt_or_drop(text, speaking)

    def _interrupt_or_drop(self, text: str, speaking: str) -> GateDispatch:
        if self._stop_gate.should_stop(text, speaking):
            return GateDispatch("interrupt")
        return GateDispatch("drop")
