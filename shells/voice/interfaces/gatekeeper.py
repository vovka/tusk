from abc import ABC, abstractmethod

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from tusk.shared.schemas.utterance import Utterance

__all__ = ["Gatekeeper"]


class Gatekeeper(ABC):
    @abstractmethod
    def evaluate(self, utterance: Utterance, recent: list[Utterance]) -> object:
        ...

    @abstractmethod
    def process(
        self,
        utterance: Utterance | BufferedUtterance,
        recent: list[Utterance],
        candidates: list[BufferedUtterance] | None = None,
    ) -> GateDispatch:
        ...
