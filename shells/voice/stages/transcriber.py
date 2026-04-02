from tusk.shared.schemas.utterance import Utterance
from tusk.shared.stt.interfaces.stt_engine import STTEngine

__all__ = ["Transcriber"]


class Transcriber:
    def __init__(self, stt_engine: STTEngine, sample_rate: int) -> None:
        self._stt = stt_engine
        self._sample_rate = sample_rate

    def process(self, utterance: Utterance) -> Utterance:
        return self._stt.transcribe(utterance.audio_frames, self._sample_rate)
