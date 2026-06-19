import importlib.util
import json
import threading
from pathlib import Path

from shells.voice.gatekeeper_slot import GatekeeperSlot
from shells.voice.stages.dictation_gatekeeper import DictationGatekeeper
from shells.voice.stages.gatekeeper import LLMGatekeeper
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
        shell = shell_class(
            self._config, self._log, stt_engine=stt_engine, gatekeeper=self._gatekeeper(),
            tts_engine=tts_engine, reporter=self._reporter,
        )
        self._control = shell
        return shell

    def _gatekeeper(self) -> GatekeeperSlot:
        registry = self._kernel.get_llm_registry()
        llm_gk = LLMGatekeeper(registry.get("gatekeeper"), self._log, follow_up_window_seconds=self._config.follow_up_timeout_seconds)
        dictation_gate = DictationGate(registry.get("gatekeeper"), self._log)
        return self._wire(llm_gk, dictation_gate)

    def _wire(self, llm_gk: LLMGatekeeper, dictation_gate: DictationGate) -> GatekeeperSlot:
        slot = GatekeeperSlot(llm_gk)
        self._kernel.set_dictation_callbacks(
            on_start=lambda: slot.swap(DictationGatekeeper(dictation_gate, self._kernel.request_dictation_stop, self._log)),
            on_stop=lambda: slot.swap(llm_gk),
        )
        return slot

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
