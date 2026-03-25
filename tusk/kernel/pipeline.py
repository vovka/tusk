from tusk.kernel.command_mode import CommandMode
from tusk.kernel.schemas.kernel_response import KernelResponse
from tusk.kernel.schemas.utterance import Utterance

__all__ = ["Pipeline"]


class Pipeline:
    def __init__(
        self,
        stt_engine: object,
        utterance_filter: object,
        gatekeeper: object,
        command_mode: CommandMode,
        dictation_router: object,
        config: object,
        log_printer: object,
    ) -> None:
        self._stt = stt_engine
        self._filter = utterance_filter
        self._gatekeeper = gatekeeper
        self._command_mode = command_mode
        self._dictation_router = dictation_router
        self._dictation_mode = None
        self._config = config
        self._log = log_printer

    def set_mode(self, mode: object | None) -> None:
        self._dictation_mode = mode

    def process_text_command(self, text: str) -> KernelResponse:
        return self._command_mode.process_command(text)

    def process_audio(self, audio: bytes, sample_rate: int) -> KernelResponse:
        utterance = self._stt.transcribe(audio, sample_rate)
        self._log_utterance(utterance)
        if utterance.confidence < 0.01:
            return KernelResponse(False, "")
        if not self._filter.is_valid(utterance):
            self._log.log("PIPELINE", "filtered utterance", "pipeline")
            return KernelResponse(False, "")
        if self._dictation_mode is not None:
            return self._dictation_mode.process_text(utterance.text)
        return self._process_command_utterance(utterance)

    def start_dictation(self, state: object) -> KernelResponse:
        from tusk.kernel.dictation_mode import AdapterDictationMode

        self._dictation_mode = AdapterDictationMode(state, self._dictation_router, self._log)
        return KernelResponse(True, "Dictation started.")

    def stop_dictation(self) -> None:
        self._dictation_mode = None

    def _log_utterance(self, utterance: Utterance) -> None:
        self._log.log("STT", f"{utterance.text!r} (confidence={utterance.confidence:.2f})")

    def _process_command_utterance(self, utterance: Utterance) -> KernelResponse:
        gate = self._gatekeeper.evaluate(utterance, self._command_mode.gatekeeper_prompt)
        return self._command_mode.handle_gate_result(gate)
