from abc import ABC, abstractmethod

from shells.voice.buffered_utterance import BufferedUtterance
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
    def mark_consumed(self, entry_id: str) -> None:
        ...

    @abstractmethod
    def mark_dropped(self, entry_id: str) -> None:
        ...

    @abstractmethod
    def mark_forwarded(self, entry_id: str) -> None:
        ...

    @abstractmethod
    def mark_recovered(self, entry_id: str) -> None:
        ...
