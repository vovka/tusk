from collections.abc import Callable

from shells.voice.gate.speech_stop_gate import SpeechStopGate
from shells.voice.interfaces.gatekeeper import Gatekeeper
from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_action import GateAction
from tusk.shared.schemas.voice.gate_dispatch import GateDispatch
from tusk.shared.schemas.voice.utterance import Utterance

__all__ = ["PlaybackGate"]


class PlaybackGate(Gatekeeper):
    """While TUSK speaks, interrupt on a stop request; otherwise pass the utterance to the inner gate."""

    # echoes of TUSK's own voice never reach this gate: EchoFilter drops them before the buffer

    def __init__(
        self,
        inner: Gatekeeper,
        current_speech_text: Callable[[], str | None],
        stop_gate: SpeechStopGate,
    ) -> None:
        self._inner = inner
        self._current_speech_text = current_speech_text
        self._stop_gate = stop_gate

    def process(self, utterance: BufferedUtterance, recent: list[Utterance], candidates: list[BufferedUtterance]) -> GateDispatch:
        speaking = self._current_speech_text()
        if speaking is not None and self._stop_gate.should_stop(utterance.text, speaking):
            return GateDispatch(GateAction.INTERRUPT)
        return self._inner.process(utterance, recent, candidates)
