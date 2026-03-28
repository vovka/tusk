from abc import ABC, abstractmethod

from tusk.kernel.schemas.utterance import Utterance

__all__ = ["UtteranceFilter"]


class UtteranceFilter(ABC):
    @abstractmethod
    def is_valid(self, utterance: Utterance) -> bool:
        ...
