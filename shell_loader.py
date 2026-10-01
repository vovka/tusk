import threading

from adapters.gnome.app_vocabulary import AppVocabulary
from shells.cli.cli_shell import CLIShell
from shells.emulator.emulator_shell import EmulatorShell
from shells.tray.tray_shell import TrayShell
from shells.voice.command_worker import CommandWorker
from shells.voice.gatekeeper_slot import GatekeeperSlot
from shells.voice.stages.chunked_speaker import ChunkedSpeaker
from shells.voice.stages.echo_filter import EchoFilter
from shells.voice.stages.sanitizer import Sanitizer
from shells.voice.stages.speech_playback import SpeechPlayback
from shells.voice.voice_shell import VoiceShell
from stt_engine_builder import SttEngineBuilder
from tts_engine_builder import TtsEngineBuilder
from voice_gatekeeper_builder import VoiceGatekeeperBuilder

__all__ = ["ShellLoader"]


class ShellLoader:
    def __init__(self, config: object, kernel: object, log: object, reporter: object, on_speech_end: object = None) -> None:
        self._config = config
        self._kernel = kernel
        self._log = log
        self._reporter = reporter
        self._on_speech_end = on_speech_end
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
            echo_filter=EchoFilter(lambda: worker.recent_speech, self._log), on_speech_end=self._on_speech_end,
            sanitizer=Sanitizer(self._log, AppVocabulary.installed().text()),
        )
        self._control = shell
        return shell

    def _stt_engine(self) -> object:
        return SttEngineBuilder(self._config).build()

    def _build_worker(self) -> CommandWorker:
        tts_engine = TtsEngineBuilder(self._config).build() if self._config.tts_enabled else None
        token = self._kernel.interrupt_token
        speaker = ChunkedSpeaker(tts_engine, SpeechPlayback(token), self._log, token)
        return CommandWorker(self._kernel.submit, speaker, self._log, token, self._config.ack_enabled)

    def _interrupt_callback(self, worker: CommandWorker) -> object:
        def request_interrupt() -> None:
            self._kernel.request_interrupt()
            worker.flush()
        return request_interrupt

    def _gatekeeper(self, worker: CommandWorker) -> GatekeeperSlot:
        return VoiceGatekeeperBuilder(self._config, self._kernel, self._log).build(worker)

    def _load_class(self, name: str) -> object:
        try:
            return _SHELL_CLASSES[name]
        except KeyError:
            raise ValueError(f"unknown shell: {name!r}") from None


_SHELL_CLASSES = {"cli": CLIShell, "emulator": EmulatorShell, "tray": TrayShell, "voice": VoiceShell}
