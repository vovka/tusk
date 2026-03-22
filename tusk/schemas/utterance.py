from dataclasses import dataclass

__all__ = ["Utterance"]


@dataclass(frozen=True)
class Utterance:
    text: str
    audio_frames: bytes
    duration_seconds: float
    confidence: float = 1.0
