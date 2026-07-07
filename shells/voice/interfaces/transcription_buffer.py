from abc import ABC, abstractmethod

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_state import GateState
from tusk.shared.schemas.utterance import Utterance

__all__ = ["TranscriptionBuffer"]


class TranscriptionBuffer(ABC):
    @abstractmethod
    def process(self, utterance: Utterance) -> BufferedUtterance | None:
        ...

    @abstractmethod
    def recent(self, count: int) -> list[Utterance]:
        ...

    @abstractmethod
    def recoverable(self, count: int, max_age_seconds: float) -> list[BufferedUtterance]:
        ...

    @abstractmethod
    def mark(self, entry_id: str, state: GateState) -> None:
        ...
