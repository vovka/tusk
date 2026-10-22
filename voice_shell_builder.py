from adapters.gnome.app_vocabulary import AppVocabulary
from shells.voice.command_worker import CommandWorker
from shells.voice.gate.gatekeeper_slot import GatekeeperSlot
from shells.voice.interfaces.gatekeeper import Gatekeeper
from shells.voice.gate.playback_gate import PlaybackGate
from shells.voice.speech.chunked_speaker import ChunkedSpeaker
from shells.voice.speech.confirmation_reply import ConfirmationReply
from shells.voice.gate.llm_gatekeeper import LLMGatekeeper
from shells.voice.gate.speech_stop_gate import SpeechStopGate
from shells.voice.gate.stop_gatekeeper import StopGatekeeper
from shells.voice.stages.sanitizer import Sanitizer
from shells.voice.speech.speech_playback import SpeechPlayback
from tusk.kernel.core.kernel_api import KernelAPI
from tusk.kernel.modes.mode_gate import ModeGate
from tusk.kernel.modes.mode_slot import ModeSlot
from tusk.providers.stt import STTEngineFactory
from tusk.providers.tts import GroqTTS, OpenAICompatibleTTS
from tusk.shared.config.config import Config
from tusk.shared.interfaces.llm_provider import LLMProvider
from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.interfaces.stt_engine import STTEngine
from tusk.shared.interfaces.tts_engine import TTSEngine

__all__ = ["VoiceShellBuilder"]

class VoiceShellBuilder:
    """Builds the voice shell's collaborators: STT/TTS engines, the command worker and the gatekeeper slot."""

    def __init__(self, config: Config, kernel: KernelAPI, log: LogPrinter) -> None:
        self._config = config
        self._kernel = kernel
        self._log = log
        self._vocabulary = AppVocabulary.installed().stt_prompt(config.stt_app_vocabulary)

    def stt_engine(self) -> STTEngine:
        factory = STTEngineFactory(self._config.groq_api_key, self._config.whisper_model_size, self._vocabulary)
        return factory.create(self._config.stt_engine)

    def tts_engine(self) -> TTSEngine:
        if self._config.tts_url:
            return OpenAICompatibleTTS(self._config.tts_url, self._config.tts_model, self._config.tts_voice)
        return GroqTTS(self._config.groq_api_key)

    def sanitizer(self, reply: ConfirmationReply | None) -> Sanitizer:
        return Sanitizer(self._log, self._vocabulary, reply)

    def worker(self) -> CommandWorker:
        tts_engine = self.tts_engine() if self._config.tts_enabled else None
        token = self._kernel.interrupt_token
        speaker = ChunkedSpeaker(tts_engine, SpeechPlayback(token), self._log, token)
        return CommandWorker(self._kernel.submit, speaker, self._log, token, self._config.ack_enabled)

    def gatekeeper(self, worker: CommandWorker) -> GatekeeperSlot:
        registry = self._kernel.llm_registry
        gk_llm = registry.get("gatekeeper") if registry else None
        stop_llm = registry.get_with_fallback("stop_gate", "gatekeeper") if registry else None
        base = self._guarded(self._base_gate(gk_llm, worker), stop_llm, worker)
        slot = GatekeeperSlot(base)
        self._wire_modes(slot, base, stop_llm, worker)
        return slot

    def _base_gate(self, gk_llm: LLMProvider | None, worker: CommandWorker) -> LLMGatekeeper:
        return LLMGatekeeper(
            gk_llm, self._log, follow_up_window_seconds=self._config.follow_up_timeout_seconds,
            is_busy=lambda: worker.is_busy, current_speech_text=lambda: worker.current_speech_text,
        )

    def _wire_modes(self, slot: GatekeeperSlot, base: Gatekeeper, stop_llm: LLMProvider | None, worker: CommandWorker) -> None:
        registry = self._kernel.llm_registry
        self._wire_mode(slot, base, stop_llm, worker, ModeGate.for_mode(registry, "dictation", self._log), self._kernel.dictation)
        self._wire_mode(slot, base, stop_llm, worker, ModeGate.for_mode(registry, "coding", self._log), self._kernel.coding)

    def _wire_mode(self, slot: GatekeeperSlot, base: Gatekeeper, stop_llm: LLMProvider | None, worker: CommandWorker,
                   gate: ModeGate, mode: ModeSlot) -> None:
        make = lambda: self._guarded(StopGatekeeper(gate, mode.request_stop, base), stop_llm, worker)
        mode.set_callbacks(lambda: slot.swap(make()), lambda: slot.swap(base))

    def _guarded(self, inner: Gatekeeper, stop_llm: LLMProvider | None, worker: CommandWorker) -> PlaybackGate:
        # while TUSK's own voice plays, only stop_gate (STOP_GATE_LLM) may interrupt; otherwise delegate to inner
        return PlaybackGate(inner, lambda: worker.current_speech_text, SpeechStopGate(stop_llm, self._log))
