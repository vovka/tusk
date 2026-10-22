import threading
from collections.abc import Callable

from shells.voice.command_worker import CommandWorker
from shells.voice.pipeline import VoicePipeline
from tusk.shared.interfaces.shell import Shell
from tusk.shared.observability.status_reporter import StatusReporter
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["VoiceShell"]


class VoiceShell(Shell):
    def __init__(
        self,
        pipeline: VoicePipeline,
        worker: CommandWorker,
        reporter: StatusReporter | None,
        pause_gate: threading.Event,
    ) -> None:
        self._pipeline = pipeline
        self._worker = worker
        self._reporter = reporter
        self._pause_gate = pause_gate

    def start(self, submit: Callable[[str], KernelResponse]) -> None:
        # the worker already holds kernel.submit; the pipeline forwards into its queue so listening never blocks
        self._worker.start()
        for _ in self._pipeline.run(self._worker.enqueue):
            pass

    def pause(self) -> None:
        self._pause_gate.clear()
        self._report(AppStatus.PAUSED)

    def resume(self) -> None:
        self._pause_gate.set()
        self._report(AppStatus.LISTENING)

    def _report(self, status: AppStatus) -> None:
        if self._reporter is not None:
            self._reporter.set_status(status)
