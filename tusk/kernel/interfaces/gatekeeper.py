from abc import ABC, abstractmethod

from tusk.kernel.schemas.gate_result import GateResult
from tusk.kernel.schemas.utterance import Utterance

__all__ = ["Gatekeeper"]


class Gatekeeper(ABC):
    @abstractmethod
    def evaluate(self, utterance: Utterance, system_prompt: str) -> GateResult:
        ...
