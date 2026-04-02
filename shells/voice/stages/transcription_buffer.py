from collections import deque

from shells.voice.interfaces.transcription_buffer import TranscriptionBuffer as TranscriptionBufferABC
from tusk.shared.schemas.utterance import Utterance

__all__ = ["TranscriptionBuffer"]


class TranscriptionBuffer(TranscriptionBufferABC):
    def __init__(self, max_utterances: int = 50) -> None:
        self._utterances: deque[Utterance] = deque(maxlen=max_utterances)

    def process(self, utterance: Utterance) -> Utterance:
        self._utterances.append(utterance)
        return utterance

    def recent(self, count: int) -> list[Utterance]:
        return list(self._utterances)[-count:]
