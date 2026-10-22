from collections.abc import Callable

from tusk.kernel.modes.adapter_mode import AdapterMode
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.status.status_reporter import StatusReporter

__all__ = ["ModeSlot"]


class ModeSlot:
    """Holds one switchable kernel mode (dictation, coding) and its wiring."""

    def __init__(
        self, app_mode: AppMode, start_reply: str, log: LogPrinter | None = None,
        reporter: StatusReporter | None = None,
        mode_factory: Callable[[object, object, object, str], object] = AdapterMode,
    ) -> None:
        self._app_mode = app_mode
        self._start_reply = start_reply
        self._log = log
        self._reporter = reporter
        self._mode_factory = mode_factory
        self._mode: object | None = None
        self._router: object | None = None
        self._on_started: Callable[[], None] | None = None
        self._on_stopped: Callable[[], None] | None = None

    @property
    def active(self) -> bool:
        return self._mode is not None

    def set_callbacks(self, on_start: Callable[[], None], on_stop: Callable[[], None]) -> None:
        self._on_started = on_start
        self._on_stopped = on_stop

    def attach_router(self, router: object) -> None:
        self._router = router

    def process_text(self, text: str) -> KernelResponse:
        if self._mode is None:
            raise RuntimeError(f"{self._app_mode.name}: process_text called with no active mode")
        return self._mode.process_text(text)

    def request_stop(self) -> KernelResponse:
        if self._mode is None:
            return KernelResponse(False, "")
        return self._mode.stop()

    def start(self, state: object) -> KernelResponse:
        self._mode = self._mode_factory(state, self._router, self._log, self._app_mode.name)
        if self._on_started is not None:
            self._on_started()
        self._report_mode(self._app_mode)
        return KernelResponse(True, self._start_reply)

    def stop(self) -> None:
        self._mode = None
        if self._on_stopped is not None:
            self._on_stopped()
        self._report_mode(AppMode.DEFAULT)

    def _report_mode(self, mode: AppMode) -> None:
        if self._reporter is not None:
            self._reporter.set_mode(mode)
