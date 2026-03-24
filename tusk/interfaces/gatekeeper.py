from abc import ABC, abstractmethod

from tusk.schemas.gate_result import GateResult
from tusk.schemas.utterance import Utterance

__all__ = ["Gatekeeper"]


class Gatekeeper(ABC):
    @abstractmethod
    def evaluate(self, utterance: Utterance, system_prompt: str) -> GateResult:
        ...
