from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.utterance import Utterance
from tusk.shared.stt.interfaces.stt_engine import STTEngine

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
