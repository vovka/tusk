import re
from collections.abc import Callable

from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_action import GateAction
from tusk.shared.schemas.voice.gate_dispatch import GateDispatch
from shells.voice.interfaces.gatekeeper import Gatekeeper
from tusk.shared.schemas.voice.utterance import Utterance

__all__ = ["PlaybackGate"]


class PlaybackGate(Gatekeeper):
    """While TUSK speaks, interrupt on stop, drop echoes of TUSK's own voice, pass real speech to the inner gate."""

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
        if self._stop_gate.should_stop(text, speaking):
            return GateDispatch(GateAction.INTERRUPT)
        if _is_echo(text, speaking):
            return GateDispatch(GateAction.DROP)
        return self._inner.process(utterance, recent, candidates)


def _is_echo(text: str, speaking: str) -> bool:
    # ponytail: substring match keeps forward-all modes from typing TUSK's voice; fuzzy match if misheard echoes leak
    heard = _words(text)
    return bool(heard) and heard in _words(speaking)


def _words(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))
