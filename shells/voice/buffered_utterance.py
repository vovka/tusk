from dataclasses import dataclass

from tusk.shared.schemas.utterance import Utterance

__all__ = ["BufferedUtterance"]


@dataclass
class BufferedUtterance:
    id: str
    utterance: Utterance
    received_at: float
    gate_state: str = "pending"

    @property
    def text(self) -> str:
        return self.utterance.text
