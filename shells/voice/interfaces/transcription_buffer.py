from abc import ABC, abstractmethod

from tusk.shared.schemas.utterance import Utterance

__all__ = ["TranscriptionBuffer"]


class TranscriptionBuffer(ABC):
    @abstractmethod
    def process(self, utterance: Utterance) -> Utterance | None:
        ...

    @abstractmethod
    def recent(self, count: int) -> list[Utterance]:
        ...
