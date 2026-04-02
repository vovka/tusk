from abc import ABC, abstractmethod

from tusk.shared.schemas.utterance import Utterance

__all__ = ["Gatekeeper"]


class Gatekeeper(ABC):
    @abstractmethod
    def evaluate(self, utterance: Utterance, recent: list[Utterance]) -> object:
        ...

    @abstractmethod
    def process(self, utterance: Utterance, recent: list[Utterance]) -> str | None:
        ...
