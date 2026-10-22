from dataclasses import dataclass

from tusk.shared.schemas.voice.utterance import Utterance

__all__ = ["BufferedUtterance"]


@dataclass
class BufferedUtterance:
    id: str
    utterance: Utterance
    received_at: float
    dropped: bool = False

    @property
    def text(self) -> str:
        return self.utterance.text
