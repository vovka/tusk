from collections.abc import Callable

from tusk.kernel.modes.coding_mode import CodingMode
from tusk.kernel.modes.dictation_mode import DictationMode
from tusk.kernel.modes.mode_state import ModeState
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.status.status_reporter import StatusReporter

__all__ = ["ModeSlot"]


class ModeSlot:
    """Holds one switchable kernel mode (dictation, coding) and routes its text."""

    def __init__(
        self, app_mode: AppMode, start_reply: str, log: LogPrinter | None = None,
        reporter: StatusReporter | None = None,
    ) -> None:
        self._app_mode = app_mode
        self._start_reply = start_reply
        self._log = log
        self._reporter = reporter
        self._state: ModeState | None = None
        self._mode: CodingMode | DictationMode | None = None
        self._on_started: Callable[[], None] | None = None
        self._on_stopped: Callable[[], None] | None = None

    @property
    def active(self) -> bool:
        return self._state is not None

    def set_callbacks(self, on_start: Callable[[], None], on_stop: Callable[[], None]) -> None:
        self._on_started = on_start
        self._on_stopped = on_stop

    def attach_mode(self, mode: CodingMode | DictationMode) -> None:
        self._mode = mode

    def process_text(self, text: str) -> KernelResponse:
        if self._state is None:
            raise RuntimeError(f"{self._app_mode.name}: process_text called with no active mode")
        result = self._mode.process(self._state, text)
        self._log_line(self._app_mode.name, result.reply or "updated")
        return result

    def request_stop(self) -> KernelResponse:
        if self._state is None:
            return KernelResponse(False, "")
        result = self._mode.stop(self._state)
        self._log_line(self._app_mode.name, result.reply or "stopped")
        self._log_line("MODE", f"{self._app_mode.name.lower()} mode ended")
        self.stop()
        return result

    def start(self, state: ModeState) -> KernelResponse:
        self._state = state
        if self._on_started is not None:
            self._on_started()
        self._report_mode(self._app_mode)
        return KernelResponse(True, self._start_reply)

    def stop(self) -> None:
        self._state = None
        if self._on_stopped is not None:
            self._on_stopped()
        self._report_mode(AppMode.DEFAULT)

    def _report_mode(self, mode: AppMode) -> None:
        if self._reporter is not None:
            self._reporter.set_mode(mode)

    def _log_line(self, tag: str, message: str) -> None:
        if self._log is not None:
            self._log.log(tag, message)
