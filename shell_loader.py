import importlib.util
import json
import threading
from pathlib import Path

from shells.voice.command_worker import CommandWorker
from shells.voice.gatekeeper_slot import GatekeeperSlot
from shells.voice.playback_gate import PlaybackGate
from shells.voice.stages.coding_gatekeeper import CodingGatekeeper
from shells.voice.stages.dictation_gatekeeper import DictationGatekeeper
from shells.voice.stages.gatekeeper import LLMGatekeeper
from shells.voice.stages.speech_playback import SpeechPlayback
from tusk.kernel.coding_gate import CodingGate
from tusk.kernel.dictation_gate import DictationGate
from tusk.providers.stt import GroqSTT
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
        stt_engine = GroqSTT(self._config.groq_api_key)
        tts_engine = GroqTTS(self._config.groq_api_key) if self._config.tts_enabled else None
        worker = self._worker(tts_engine)
        shell = shell_class(
            self._config, self._log, stt_engine=stt_engine, gatekeeper=self._gatekeeper(worker),
            tts_engine=tts_engine, reporter=self._reporter, command_worker=worker,
            request_interrupt=self._kernel.request_interrupt, interrupt_token=self._kernel.interrupt_token,
        )
        self._control = shell
        return shell

    def _worker(self, tts_engine: object | None) -> CommandWorker:
        playback = SpeechPlayback(self._kernel.interrupt_token)
        return CommandWorker(tts_engine, playback, self._log, self._kernel.interrupt_token)

    def _gatekeeper(self, worker: CommandWorker) -> GatekeeperSlot:
        gk_llm = self._kernel.get_llm_registry().get("gatekeeper")
        llm_gk = LLMGatekeeper(
            gk_llm, self._log, follow_up_window_seconds=self._config.follow_up_timeout_seconds,
            is_busy=lambda: worker.is_busy, current_speech_text=lambda: worker.current_speech_text,
        )
        slot = GatekeeperSlot(llm_gk)
        self._wire_dictation(slot, llm_gk, gk_llm, worker)
        self._wire_coding(slot, llm_gk, gk_llm, worker)
        return slot

    def _wire_dictation(self, slot: GatekeeperSlot, llm_gk: LLMGatekeeper, gk_llm: object, worker: CommandWorker) -> None:
        gate = DictationGate(gk_llm, self._log)
        self._kernel.set_dictation_callbacks(
            on_start=lambda: slot.swap(self._playback_gate(DictationGatekeeper(gate, self._kernel.request_dictation_stop, self._log), gk_llm, worker)),
            on_stop=lambda: slot.swap(llm_gk),
        )

    def _wire_coding(self, slot: GatekeeperSlot, llm_gk: LLMGatekeeper, gk_llm: object, worker: CommandWorker) -> None:
        gate = CodingGate(gk_llm, self._log)
        self._kernel.set_coding_callbacks(
            on_start=lambda: slot.swap(self._playback_gate(CodingGatekeeper(gate, self._kernel.request_coding_stop, self._log), gk_llm, worker)),
            on_stop=lambda: slot.swap(llm_gk),
        )

    def _playback_gate(self, inner: object, gk_llm: object, worker: CommandWorker) -> PlaybackGate:
        return PlaybackGate(inner, gk_llm, self._log, lambda: worker.current_speech_text)

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
