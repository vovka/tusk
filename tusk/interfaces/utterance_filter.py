from abc import ABC, abstractmethod

from tusk.schemas.utterance import Utterance

__all__ = ["UtteranceFilter"]


class UtteranceFilter(ABC):
    @abstractmethod
    def is_valid(self, utterance: Utterance) -> bool:
        """Return True if the utterance should proceed to the gatekeeper."""
        ...
