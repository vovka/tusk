import threading
from collections.abc import Callable

from shells.voice.command_worker import CommandWorker
from shells.voice.interfaces.gatekeeper import Gatekeeper
from shells.voice.pipeline import VoicePipeline
from shells.voice.stages.audio_capture import AudioCapture
from shells.voice.stages.echo_filter import EchoFilter
from shells.voice.stages.sanitizer import Sanitizer
from shells.voice.stages.transcriber import Transcriber
from shells.voice.stages.transcription_buffer import TranscriptionBuffer
from shells.voice.stages.utterance_detector import UtteranceDetector
from tusk.shared.config.config import Config
from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.interfaces.stt_engine import STTEngine
from tusk.shared.observability.status_reporter import StatusReporter
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["VoiceShell"]


class VoiceShell:
    def __init__(
        self,
        config: Config,
        log_printer: LogPrinter,
        stt_engine: STTEngine | None = None,
        gatekeeper: Gatekeeper | None = None,
        pipeline: VoicePipeline | None = None,
        worker: CommandWorker | None = None,
        reporter: StatusReporter | None = None,
        on_interrupt: Callable[[], None] | None = None,
        echo_filter: EchoFilter | None = None,
        on_speech_end: Callable[[float], None] | None = None,
        sanitizer: Sanitizer | None = None,
    ) -> None:
        self._reporter = reporter
        self._pause_gate = threading.Event()
        self._pause_gate.set()
        self._worker = worker
        self._on_interrupt = on_interrupt
        self._echo_filter, self._on_speech_end = echo_filter, on_speech_end
        self._sanitizer = sanitizer or Sanitizer(log_printer)
        self._pipeline = pipeline or self._build_pipeline(config, log_printer, stt_engine, gatekeeper)
        self._log = log_printer
        self._running = True

    def start(self, submit: Callable[..., KernelResponse]) -> None:
        if self._worker is not None:
            self._worker.start()
        target = self._worker.enqueue if self._worker is not None else lambda text, refrain="", kind="conversation": submit(text, kind)
        for result in self._pipeline.run(target):
            if not self._running:
                return
            self._log_reply(result)

    def stop(self) -> None:
        self._running = False

    def pause(self) -> None:
        self._pause_gate.clear()
        self._report(AppStatus.PAUSED)

    def resume(self) -> None:
        self._pause_gate.set()
        self._report(AppStatus.LISTENING)

    def _report(self, status: AppStatus) -> None:
        if self._reporter is not None:
            self._reporter.set_status(status)

    def _build_pipeline(
        self,
        config: Config,
        log_printer: LogPrinter,
        stt_engine: STTEngine | None,
        gatekeeper: Gatekeeper | None,
    ) -> VoicePipeline:
        _require_pipeline_inputs(stt_engine, gatekeeper)
        return VoicePipeline(
            self._detector(config, log_printer),
            Transcriber(stt_engine, config.audio_sample_rate, log_printer),
            self._sanitizer,
            TranscriptionBuffer(log_printer),
            gatekeeper,
            config.gate_recovery_window_seconds, config.gate_recovery_candidate_limit, self._reporter, self._on_interrupt, self._echo_filter,
        )

    def _detector(self, config: Config, log_printer: LogPrinter) -> UtteranceDetector:
        return UtteranceDetector(
            AudioCapture(config.audio_sample_rate, config.audio_frame_duration_ms, self._pause_gate),
            config.audio_sample_rate,
            config.vad_aggressiveness,
            log_printer,
            frame_duration_ms=config.audio_frame_duration_ms,
            silence_ms=config.vad_silence_ms,
            on_speech_end=self._on_speech_end,
        )

    def _log_reply(self, result: KernelResponse) -> None:
        reply = getattr(result, "reply", "")
        if not reply:
            return
        self._log.log("TUSK", reply)


def _require_pipeline_inputs(stt_engine: STTEngine | None, gatekeeper: Gatekeeper | None) -> None:
    if stt_engine is None:
        raise ValueError("voice shell requires an STT engine")
    if gatekeeper is None:
        raise ValueError("voice shell requires a gatekeeper")
