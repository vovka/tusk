import types

from shells.voice.pipeline import VoicePipeline
from shells.voice.stages.audio_capture import AudioCapture
from shells.voice.stages.sanitizer import Sanitizer
from shells.voice.stages.transcriber import Transcriber
from shells.voice.stages.transcription_buffer import TranscriptionBuffer
from shells.voice.stages.utterance_detector import UtteranceDetector

__all__ = ["VoiceShell"]


class VoiceShell:
    def __init__(
        self,
        config: object,
        log_printer: object,
        stt_engine: object | None = None,
        gatekeeper: object | None = None,
        pipeline: object | None = None,
    ) -> None:
        self._pipeline = pipeline or self._build_pipeline(config, log_printer, stt_engine, gatekeeper)
        self._log = log_printer
        self._running = True

    def start(self, submit: object) -> None:
        for result in self._pipeline.run(submit):
            if not self._running:
                return
            self._log_reply(result)

    def stop(self) -> None:
        self._running = False

    def _build_pipeline(
        self,
        config: object,
        log_printer: object,
        stt_engine: object | None,
        gatekeeper: object | None,
    ) -> VoicePipeline:
        detector = UtteranceDetector(
            AudioCapture(config.audio_sample_rate, config.audio_frame_duration_ms),
            config.audio_sample_rate,
            config.vad_aggressiveness,
            log_printer,
        )
        transcriber = Transcriber(stt_engine or _missing_stt_engine(), config.audio_sample_rate)
        buffer = TranscriptionBuffer()
        return VoicePipeline(detector, transcriber, Sanitizer(), buffer, gatekeeper or _drop_all_gatekeeper())

    def _log_reply(self, result: object) -> None:
        reply = getattr(result, "reply", "")
        if reply:
            self._log.log("TUSK", reply)


def _missing_stt_engine() -> object:
    return types.SimpleNamespace(transcribe=_raise_missing_stt)


def _drop_all_gatekeeper() -> object:
    return types.SimpleNamespace(process=lambda utterance, recent: None)


def _raise_missing_stt(audio_frames: bytes, sample_rate: int) -> object:
    raise RuntimeError("voice shell requires an STT engine")
