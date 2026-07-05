import threading
import types

from shells.voice.gate_dispatch import GateDispatch
from shells.voice.pipeline import VoicePipeline
from shells.voice.stages.audio_capture import AudioCapture
from shells.voice.stages.sanitizer import Sanitizer
from shells.voice.stages.transcriber import Transcriber
from shells.voice.stages.transcription_buffer import TranscriptionBuffer
from shells.voice.stages.utterance_detector import UtteranceDetector
from tusk.shared.schemas.app_status import AppStatus

__all__ = ["VoiceShell"]


class VoiceShell:
    def __init__(
        self,
        config: object,
        log_printer: object,
        stt_engine: object | None = None,
        gatekeeper: object | None = None,
        pipeline: object | None = None,
        worker: object | None = None,
        reporter: object | None = None,
        on_interrupt: object | None = None,
    ) -> None:
        self._reporter = reporter
        self._pause_gate = threading.Event()
        self._pause_gate.set()
        self._worker = worker
        self._on_interrupt = on_interrupt
        self._pipeline = pipeline or self._build_pipeline(config, log_printer, stt_engine, gatekeeper)
        self._log = log_printer
        self._running = True

    def start(self, submit: object) -> None:
        if self._worker is not None:
            self._worker.start()
        target = self._worker.enqueue if self._worker is not None else submit
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
        config: object,
        log_printer: object,
        stt_engine: object | None,
        gatekeeper: object | None,
    ) -> VoicePipeline:
        settings = _pipeline_settings(config)
        return VoicePipeline(
            self._detector(config, log_printer),
            Transcriber(stt_engine or _missing_stt_engine(), config.audio_sample_rate, log_printer),
            Sanitizer(log_printer),
            TranscriptionBuffer(log_printer),
            gatekeeper or _drop_all_gatekeeper(),
            settings[0],
            settings[1], self._reporter, self._on_interrupt,
        )

    def _detector(self, config: object, log_printer: object) -> UtteranceDetector:
        return UtteranceDetector(
            AudioCapture(config.audio_sample_rate, config.audio_frame_duration_ms, self._pause_gate),
            config.audio_sample_rate,
            config.vad_aggressiveness,
            log_printer,
        )

    def _log_reply(self, result: object) -> None:
        reply = getattr(result, "reply", "")
        if not reply:
            return
        self._log.log("TUSK", reply)


def _missing_stt_engine() -> object:
    return types.SimpleNamespace(transcribe=_raise_missing_stt)


def _drop_all_gatekeeper() -> object:
    return types.SimpleNamespace(process=lambda utterance, recent, candidates=None: GateDispatch("drop"))


def _pipeline_settings(config: object) -> tuple[float, int]:
    return getattr(config, "gate_recovery_window_seconds", 60.0), getattr(config, "gate_recovery_candidate_limit", 6)


def _raise_missing_stt(audio_frames: bytes, sample_rate: int) -> object:
    raise RuntimeError("voice shell requires an STT engine")
