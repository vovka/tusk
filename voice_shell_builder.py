import threading
from collections.abc import Callable

from adapters.gnome.app_vocabulary import AppVocabulary
from gatekeeper_builder import GatekeeperBuilder
from shells.voice.command_worker import CommandWorker
from shells.voice.gate.confirmation_answer_gate import ConfirmationAnswerGate
from shells.voice.pipeline import VoicePipeline
from shells.voice.speech.chunked_speaker import ChunkedSpeaker
from shells.voice.speech.confirmation_reply import ConfirmationReply
from shells.voice.speech.speech_playback import SpeechPlayback
from shells.voice.stages.audio_capture import AudioCapture
from shells.voice.stages.echo_filter import EchoFilter
from shells.voice.stages.sanitizer import Sanitizer
from shells.voice.stages.transcriber import Transcriber
from shells.voice.stages.transcription_buffer import TranscriptionBuffer
from shells.voice.stages.utterance_detector import UtteranceDetector
from shells.voice.voice_shell import VoiceShell
from tusk.kernel.core.kernel_api import KernelAPI
from tusk.providers.stt import STTEngineFactory
from tusk.providers.tts import GroqTTS, OpenAICompatibleTTS
from tusk.shared.config.config import Config
from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.interfaces.stt_engine import STTEngine
from tusk.shared.interfaces.tts_engine import TTSEngine
from tusk.shared.observability.status_reporter import StatusReporter

__all__ = ["VoiceShellBuilder"]


class VoiceShellBuilder:
    """Builds a ready VoiceShell: STT/TTS engines, command worker, gatekeeper chain, pipeline and pause gate."""

    def __init__(
        self,
        config: Config,
        kernel: KernelAPI,
        log: LogPrinter,
        reporter: StatusReporter | None,
        on_speech_end: Callable[[float], None] | None,
    ) -> None:
        self._config = config
        self._kernel = kernel
        self._log = log
        self._reporter = reporter
        self._on_speech_end = on_speech_end
        self._vocabulary = AppVocabulary.installed().stt_prompt(config.stt_app_vocabulary)
        self._gates = GatekeeperBuilder(config, kernel, log)

    def build(self) -> VoiceShell:
        worker = self.worker()
        pause_gate = threading.Event()
        pause_gate.set()
        return VoiceShell(self._pipeline(worker, pause_gate), worker, self._reporter, pause_gate)

    def stt_engine(self) -> STTEngine:
        factory = STTEngineFactory(self._config.groq_api_key, self._config.whisper_model_size, self._vocabulary)
        return factory.create(self._config.stt_engine)

    def tts_engine(self) -> TTSEngine:
        if self._config.tts_url:
            return OpenAICompatibleTTS(self._config.tts_url, self._config.tts_model, self._config.tts_voice)
        return GroqTTS(self._config.groq_api_key)

    def worker(self) -> CommandWorker:
        tts_engine = self.tts_engine() if self._config.tts_enabled else None
        token = self._kernel.interrupt_token
        speaker = ChunkedSpeaker(tts_engine, SpeechPlayback(token), self._log, token)
        return CommandWorker(self._kernel.submit, speaker, self._log, token, self._config.ack_enabled)

    def _pipeline(self, worker: CommandWorker, pause_gate: threading.Event) -> VoicePipeline:
        reply = ConfirmationReply(lambda: worker.recent_speech)
        return VoicePipeline(
            self._detector(pause_gate),
            Transcriber(self.stt_engine(), self._config.audio_sample_rate, self._log),
            Sanitizer(self._log, self._vocabulary, reply),
            TranscriptionBuffer(self._log),
            ConfirmationAnswerGate(self._gates.gatekeeper(worker), reply),
            self._config.gate_recovery_window_seconds, self._config.gate_recovery_candidate_limit,
            self._reporter, self._interrupt(worker), EchoFilter(lambda: worker.recent_speech, self._log),
        )

    def _detector(self, pause_gate: threading.Event) -> UtteranceDetector:
        config = self._config
        return UtteranceDetector(
            AudioCapture(config.audio_sample_rate, config.audio_frame_duration_ms, pause_gate),
            config.audio_sample_rate, config.vad_aggressiveness, self._log,
            frame_duration_ms=config.audio_frame_duration_ms, silence_ms=config.vad_silence_ms, on_speech_end=self._on_speech_end,
        )

    def _interrupt(self, worker: CommandWorker) -> Callable[[], None]:
        def request_interrupt() -> None:
            self._kernel.request_interrupt()
            worker.flush()
        return request_interrupt
