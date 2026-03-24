from abc import ABC, abstractmethod

from tusk.schemas.utterance import Utterance

__all__ = ["STTEngine"]


class STTEngine(ABC):
    @abstractmethod
    def transcribe(self, audio_frames: bytes, sample_rate: int) -> Utterance:
        ...
