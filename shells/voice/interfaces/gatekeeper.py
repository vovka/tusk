from abc import ABC, abstractmethod

from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_dispatch import GateDispatch
from tusk.shared.schemas.voice.utterance import Utterance

__all__ = ["Gatekeeper"]


class Gatekeeper(ABC):
    @abstractmethod
    def process(
        self,
        utterance: Utterance | BufferedUtterance,
        recent: list[Utterance],
        candidates: list[BufferedUtterance] | None = None,
    ) -> GateDispatch:
        ...
