from tusk.config import Config
from tusk.core.utterance_detector import UtteranceDetector
from tusk.interfaces.gatekeeper import Gatekeeper
from tusk.interfaces.log_printer import LogPrinter
from tusk.interfaces.pipeline_controller import PipelineController
from tusk.interfaces.pipeline_mode import PipelineMode
from tusk.interfaces.stt_engine import STTEngine
from tusk.schemas.utterance import Utterance

__all__ = ["Pipeline"]


class Pipeline(PipelineController):
    def __init__(
        self,
        utterance_detector: UtteranceDetector,
        stt_engine: STTEngine,
        gatekeeper: Gatekeeper,
        initial_mode: PipelineMode,
        config: Config,
        log_printer: LogPrinter,
    ) -> None:
        self._detector = utterance_detector
        self._stt = stt_engine
        self._gatekeeper = gatekeeper
        self._current_mode = initial_mode
        self._config = config
        self._log = log_printer

    def set_mode(self, mode: PipelineMode) -> None:
        self._log.log("PIPELINE", f"mode → {type(mode).__name__}")
        self._current_mode = mode

    def run(self) -> None:
        self._log.log("PIPELINE", "TUSK listening...")
        for utterance in self._detector.stream_utterances():
            try:
                self._process_utterance(utterance)
            except Exception as exc:
                self._log.log("ERROR", str(exc))

    def _process_utterance(self, utterance: Utterance) -> None:
        transcribed = self._transcribe(utterance)
        if transcribed is None:
            return
        prompt = self._current_mode.gatekeeper_prompt
        gate = self._gatekeeper.evaluate(transcribed, prompt)
        self._current_mode.handle_utterance(gate, transcribed, self)

    def _transcribe(self, utterance: Utterance) -> Utterance | None:
        result = self._stt.transcribe(utterance.audio_frames, self._config.audio_sample_rate)
        self._log.log("STT", f"{result.text!r} (confidence={result.confidence:.2f})")
        if result.confidence < 0.01:
            self._log.log("STT", "low confidence, discarded")
            return None
        return result
