import importlib.util
import json
import threading
from pathlib import Path

from shells.voice.command_worker import CommandWorker
from shells.voice.gatekeeper_slot import GatekeeperSlot
from shells.voice.playback_gate import PlaybackGate
from shells.voice.stages.stop_gatekeeper import StopGatekeeper
from shells.voice.stages.gatekeeper import LLMGatekeeper
from shells.voice.stages.speech_playback import SpeechPlayback
from shells.voice.stages.speech_stop_gate import SpeechStopGate
from tusk.kernel.coding_gate_prompt import CODING_GATE_PROMPT
from tusk.kernel.dictation_gate_prompt import DICTATION_GATE_PROMPT
from tusk.kernel.mode_gate import ModeGate
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
        return CommandWorker(self._kernel.submit, tts_engine, SpeechPlayback(token), self._log, token)

    def _interrupt_callback(self, worker: CommandWorker) -> object:
        def request_interrupt() -> None:
            self._kernel.request_interrupt()
            worker.flush()
        return request_interrupt

    def _gatekeeper(self, worker: CommandWorker) -> GatekeeperSlot:
        gk_llm = self._kernel.get_llm_registry().get("gatekeeper")
        llm_gk = LLMGatekeeper(
            gk_llm, self._log, follow_up_window_seconds=self._config.follow_up_timeout_seconds,
            is_busy=lambda: worker.is_busy, current_speech_text=lambda: worker.current_speech_text,
        )
        slot = GatekeeperSlot(llm_gk)
        self._wire_modes(slot, llm_gk, gk_llm, worker)
        return slot

    def _wire_modes(self, slot: GatekeeperSlot, llm_gk: LLMGatekeeper, gk_llm: object, worker: CommandWorker) -> None:
        self._wire_mode(slot, llm_gk, gk_llm, worker, "dictation", DICTATION_GATE_PROMPT,
                        self._kernel.set_dictation_callbacks, self._kernel.request_dictation_stop)
        self._wire_mode(slot, llm_gk, gk_llm, worker, "coding", CODING_GATE_PROMPT,
                        self._kernel.set_coding_callbacks, self._kernel.request_coding_stop)

    def _wire_mode(self, slot: GatekeeperSlot, llm_gk: LLMGatekeeper, gk_llm: object, worker: CommandWorker,
                   name: str, prompt: str, set_callbacks: object, request_stop: object) -> None:
        gate = ModeGate(gk_llm, name, prompt, self._log)
        make = lambda: self._guarded(StopGatekeeper(gate, request_stop), gk_llm, worker)
        set_callbacks(on_start=lambda: slot.swap(make()), on_stop=lambda: slot.swap(llm_gk))

    def _guarded(self, inner: object, gk_llm: object, worker: CommandWorker) -> PlaybackGate:
        # forward-all mode gates only ever see interrupt-or-drop while TUSK's own voice plays
        return PlaybackGate(inner, lambda: worker.current_speech_text, SpeechStopGate(gk_llm, self._log))

    def _load_class(self, name: str) -> object:
        manifest = json.loads((Path("shells") / name / "shell.json").read_text())
        module = self._load_module(name, manifest["entry_module"])
        return getattr(module, manifest["entry_class"])

    def _load_module(self, name: str, module_name: str) -> object:
        path = Path("shells") / name / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(f"shells.{name}.{module_name}", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
