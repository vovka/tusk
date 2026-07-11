import threading

from shells.cli.cli_shell import CLIShell
from shells.emulator.emulator_shell import EmulatorShell
from shells.tray.tray_shell import TrayShell
from shells.voice.command_worker import CommandWorker
from shells.voice.gatekeeper_slot import GatekeeperSlot
from shells.voice.playback_gate import PlaybackGate
from shells.voice.stages.gate.stop_gatekeeper import StopGatekeeper
from shells.voice.stages.gate.gatekeeper import LLMGatekeeper
from shells.voice.stages.chunked_speaker import ChunkedSpeaker
from shells.voice.stages.speech_playback import SpeechPlayback
from shells.voice.stages.gate.speech_stop_gate import SpeechStopGate
from shells.voice.voice_shell import VoiceShell
from tusk.providers.stt import STTEngineFactory
from tusk.providers.tts import GroqTTS

__all__ = ["ShellLoader"]


class ShellLoader:
    def __init__(self, config: object, kernel: object, log: object, reporter: object) -> None:
        self._config = config
        self._kernel = kernel
        self._log = log
        self._reporter = reporter
        self._shutdown_event = threading.Event()
        self._control: object | None = None

    def start(self) -> None:
        shells = [self._build(name) for name in self._ordered_names()]
        self._log.log("READY", "TUSK is ready.", "startup")
        self._run(shells)

    def _ordered_names(self) -> list[str]:
        names = [name for name in self._config.shells if name != "tray"]
        if "tray" in self._config.shells:
            names.append("tray")
        return names

    def _run(self, shells: list[object]) -> None:
        for shell in shells[:-1]:
            threading.Thread(target=shell.start, args=(self._kernel.submit,), daemon=True).start()
        if shells:
            shells[-1].start(self._kernel.submit)

    def _build(self, name: str) -> object:
        shell_class = self._load_class(name)
        if name == "voice":
            return self._build_voice(shell_class)
        if name == "tray":
            return shell_class(self._reporter, self._control, self._shutdown_event, self._config)
        return shell_class()

    def _build_voice(self, shell_class: object) -> object:
        stt_engine = self._stt_engine()
        worker = self._build_worker()
        shell = shell_class(
            self._config, self._log, stt_engine=stt_engine, gatekeeper=self._gatekeeper(worker),
            worker=worker, reporter=self._reporter, on_interrupt=self._interrupt_callback(worker),
        )
        self._control = shell
        return shell

    def _stt_engine(self) -> object:
        factory = STTEngineFactory(self._config.groq_api_key, self._config.whisper_model_size)
        return factory.create(self._config.stt_engine)

    def _build_worker(self) -> CommandWorker:
        tts_engine = GroqTTS(self._config.groq_api_key) if self._config.tts_enabled else None
        token = self._kernel.interrupt_token
        speaker = ChunkedSpeaker(tts_engine, SpeechPlayback(token), self._log, token)
        return CommandWorker(self._kernel.submit, speaker, self._log, token, self._config.ack_enabled)

    def _interrupt_callback(self, worker: CommandWorker) -> object:
        def request_interrupt() -> None:
            self._kernel.request_interrupt()
            worker.flush()
        return request_interrupt

    def _gatekeeper(self, worker: CommandWorker) -> GatekeeperSlot:
        registry = self._kernel.get_llm_registry()
        gk_llm = registry.get("gatekeeper") if registry else None
        stop_llm = registry.get_with_fallback("stop_gate", "gatekeeper") if registry else None
        base = self._guarded(self._base_gate(gk_llm, worker), stop_llm, worker)
        slot = GatekeeperSlot(base)
        self._wire_modes(slot, base, stop_llm, worker)
        return slot

    def _base_gate(self, gk_llm: object, worker: CommandWorker) -> LLMGatekeeper:
        return LLMGatekeeper(
            gk_llm, self._log, follow_up_window_seconds=self._config.follow_up_timeout_seconds,
            is_busy=lambda: worker.is_busy, current_speech_text=lambda: worker.current_speech_text,
        )

    def _wire_modes(self, slot: GatekeeperSlot, base: object, stop_llm: object, worker: CommandWorker) -> None:
        self._wire_mode(slot, base, stop_llm, worker, self._kernel.dictation_gate(),
                        self._kernel.set_dictation_callbacks, self._kernel.request_dictation_stop)
        self._wire_mode(slot, base, stop_llm, worker, self._kernel.coding_gate(),
                        self._kernel.set_coding_callbacks, self._kernel.request_coding_stop)

    def _wire_mode(self, slot: GatekeeperSlot, base: object, stop_llm: object, worker: CommandWorker,
                   gate: object, set_callbacks: object, request_stop: object) -> None:
        make = lambda: self._guarded(StopGatekeeper(gate, request_stop), stop_llm, worker)
        set_callbacks(on_start=lambda: slot.swap(make()), on_stop=lambda: slot.swap(base))

    def _guarded(self, inner: object, stop_llm: object, worker: CommandWorker) -> PlaybackGate:
        # while TUSK's own voice plays, only stop_gate (STOP_GATE_LLM) may interrupt; otherwise delegate to inner
        return PlaybackGate(inner, lambda: worker.current_speech_text, SpeechStopGate(stop_llm, self._log))

    def _load_class(self, name: str) -> object:
        try:
            return _SHELL_CLASSES[name]
        except KeyError:
            raise ValueError(f"unknown shell: {name!r}") from None


_SHELL_CLASSES = {"cli": CLIShell, "emulator": EmulatorShell, "tray": TrayShell, "voice": VoiceShell}
