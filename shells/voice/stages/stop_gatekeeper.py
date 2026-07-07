from collections.abc import Callable

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.interfaces.gatekeeper import Gatekeeper
from tusk.shared.schemas.utterance import Utterance

__all__ = ["StopGatekeeper"]


class StopGatekeeper(Gatekeeper):
    """Forward-all gatekeeper for an active mode: only a stop intent breaks the flow."""

    def __init__(self, gate: object, stop_callback: Callable[[], None]) -> None:
        self._gate = gate
        self._stop = stop_callback

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
