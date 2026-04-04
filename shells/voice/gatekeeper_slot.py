from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.interfaces.gatekeeper import Gatekeeper
from tusk.shared.schemas.utterance import Utterance

__all__ = ["GatekeeperSlot"]


class GatekeeperSlot(Gatekeeper):
    def __init__(self, inner: Gatekeeper) -> None:
        self._inner = inner

    def swap(self, gatekeeper: Gatekeeper) -> None:
        self._inner = gatekeeper

    def evaluate(self, utterance: Utterance, recent: list[Utterance]) -> object:
        return self._inner.evaluate(utterance, recent)

    def process(
        self,
        utterance: Utterance | BufferedUtterance,
        recent: list[Utterance],
        candidates: list[BufferedUtterance] | None = None,
    ) -> GateDispatch:
        return self._inner.process(utterance, recent, candidates)
