import threading
from collections.abc import Callable

from composition.voice_shell_builder import VoiceShellBuilder
from shells.cli_shell import CLIShell
from shells.emulator_shell import EmulatorShell
from shells.tray.tray_shell import TrayShell
from shells.voice.voice_shell import VoiceShell
from tusk.kernel.core.kernel_api import KernelAPI
from tusk.shared.config.config import Config
from tusk.shared.interfaces.shell import Shell
from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.observability.status_reporter import StatusReporter

__all__ = ["ShellLoader"]


class ShellLoader:
    def __init__(
        self,
        config: Config,
        kernel: KernelAPI,
        log: LogPrinter,
        reporter: StatusReporter,
        on_speech_end: Callable[[float], None] | None = None,
    ) -> None:
        self._config = config
        self._kernel = kernel
        self._log = log
        self._reporter = reporter
        self._on_speech_end = on_speech_end
        self._shutdown_event = threading.Event()
        self._control: VoiceShell | None = None

    def start(self) -> None:
        shells = [self._build(name) for name in self._ordered_names()]
        self._log.log("READY", "TUSK is ready.", "startup")
        self._run(shells)

    def _ordered_names(self) -> list[str]:
        names = [name for name in self._config.shells if name != "tray"]
        if "tray" in self._config.shells:
            names.append("tray")
        return names

    def _run(self, shells: list[Shell]) -> None:
        for shell in shells[:-1]:
            threading.Thread(target=shell.start, args=(self._kernel.submit,), daemon=True).start()
        if shells:
            shells[-1].start(self._kernel.submit)

    def _build(self, name: str) -> Shell:
        if name == "voice":
            return self._build_voice()
        shell_class = self._load_class(name)
        if name == "tray":
            return self._build_tray(shell_class)
        return shell_class()

    def _build_tray(self, tray_class: type[Shell]) -> Shell:
        voice = self._control
        if voice is None:
            return tray_class(self._reporter, None, None, self._shutdown_event, self._config)
        return tray_class(self._reporter, voice.pause, voice.resume, self._shutdown_event, self._config)

    def _build_voice(self) -> VoiceShell:
        self._control = VoiceShellBuilder(self._config, self._kernel, self._log, self._reporter, self._on_speech_end).build()
        return self._control

    def _load_class(self, name: str) -> type[Shell]:
        try:
            return _SHELL_CLASSES[name]
        except KeyError:
            raise ValueError(f"unknown shell: {name!r}") from None


_SHELL_CLASSES: dict[str, type[Shell]] = {"cli": CLIShell, "emulator": EmulatorShell, "tray": TrayShell}
