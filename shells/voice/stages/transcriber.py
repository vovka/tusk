from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.interfaces.stt_engine import STTEngine
from tusk.shared.schemas.voice.utterance import Utterance

__all__ = ["Transcriber"]


class Transcriber:
    def __init__(self, stt_engine: STTEngine, sample_rate: int, log_printer: LogPrinter | None = None) -> None:
        self._stt = stt_engine
        self._sample_rate = sample_rate
        self._log = log_printer

    def process(self, utterance: Utterance) -> Utterance:
        result = self._stt.transcribe(utterance.audio_frames, self._sample_rate)
        if self._log:
            self._log.log("TRANSCRIBER", f"text={result.text!r}", "transcriber")
        return result
