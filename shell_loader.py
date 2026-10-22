import threading
from collections.abc import Callable

from shells.cli.cli_shell import CLIShell
from shells.emulator.emulator_shell import EmulatorShell
from shells.tray.tray_shell import TrayShell
from shells.voice.command_worker import CommandWorker
from shells.voice.confirmation_answer_gate import ConfirmationAnswerGate
from shells.voice.stages.confirmation_reply import ConfirmationReply
from shells.voice.stages.echo_filter import EchoFilter
from shells.voice.voice_shell import VoiceShell
from tusk.kernel.core.kernel_api import KernelAPI
from tusk.shared.config.config import Config
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.status.status_reporter import StatusReporter
from voice_shell_builder import VoiceShellBuilder

__all__ = ["ShellLoader"]

Shell = CLIShell | EmulatorShell | TrayShell | VoiceShell


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
        shell_class = self._load_class(name)
        if name == "voice":
            return self._build_voice(shell_class)
        if name == "tray":
            return shell_class(self._reporter, self._control, self._shutdown_event, self._config)
        return shell_class()

    def _build_voice(self, shell_class: type[VoiceShell]) -> VoiceShell:
        builder = VoiceShellBuilder(self._config, self._kernel, self._log)
        worker = builder.worker()
        reply = ConfirmationReply(lambda: worker.recent_speech)
        shell = shell_class(
            self._config, self._log, stt_engine=builder.stt_engine(), gatekeeper=ConfirmationAnswerGate(builder.gatekeeper(worker), reply),
            worker=worker, reporter=self._reporter, on_interrupt=self._interrupt_callback(worker),
            echo_filter=EchoFilter(lambda: worker.recent_speech, self._log), on_speech_end=self._on_speech_end,
            sanitizer=builder.sanitizer(reply))
        self._control = shell
        return shell

    def _interrupt_callback(self, worker: CommandWorker) -> Callable[[], None]:
        def request_interrupt() -> None:
            self._kernel.request_interrupt()
            worker.flush()
        return request_interrupt

    def _load_class(self, name: str) -> type[Shell]:
        try:
            return _SHELL_CLASSES[name]
        except KeyError:
            raise ValueError(f"unknown shell: {name!r}") from None


_SHELL_CLASSES: dict[str, type[Shell]] = {"cli": CLIShell, "emulator": EmulatorShell, "tray": TrayShell, "voice": VoiceShell}
