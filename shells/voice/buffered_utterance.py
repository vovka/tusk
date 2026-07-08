from dataclasses import dataclass

from shells.voice.gate_state import GateState
from tusk.shared.schemas.utterance import Utterance

__all__ = ["BufferedUtterance"]


@dataclass
class BufferedUtterance:
    id: str
    utterance: Utterance
    received_at: float
    gate_state: GateState = GateState.PENDING

    @property
    def text(self) -> str:
        return self.utterance.text
