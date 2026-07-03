from collections.abc import Callable

from tusk.kernel.submit_status_reporter import SubmitStatusReporter
from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["KernelAPI"]


class KernelAPI:
    def __init__(
        self,
        command_mode: object,
        llm_registry: object,
        log: object | None = None,
        reporter: object | None = None,
    ) -> None:
        self._command_mode = command_mode
        self._llm_registry = llm_registry
        self._log = log
        self._reporter = reporter
        self._submit_reporter = SubmitStatusReporter(reporter) if reporter is not None else None
        self._init_state()

    def _init_state(self) -> None:
        self._dictation_mode = None
        self._dictation_router = None
        self._coding_mode = None
        self._coding_router = None
        self._on_dictation_started: Callable[[], None] | None = None
        self._on_dictation_stopped: Callable[[], None] | None = None
        self._on_coding_started: Callable[[], None] | None = None
        self._on_coding_stopped: Callable[[], None] | None = None

    def submit(self, text: str) -> KernelResponse:
        self._log_input(text)
        if self._submit_reporter is None:
            return self._route(text)
        return self._submit_reporter.run(text, self._route)

    def _log_input(self, text: str) -> None:
        if self._log is not None:
            self._log.log("KERNELINPUT", f"text={text!r}", "kernel-input")

    def _route(self, text: str) -> KernelResponse:
        if self._coding_mode is not None:
            return self._coding_mode.process_text(text)
        if self._dictation_mode is not None:
            return self._dictation_mode.process_text(text)
        return self._command_mode.process_command(text)

    def _report_mode(self, mode: AppMode) -> None:
        if self._reporter is not None:
            self._reporter.set_mode(mode)

    def set_dictation_callbacks(
        self, on_start: Callable[[], None], on_stop: Callable[[], None]
    ) -> None:
        self._on_dictation_started = on_start
        self._on_dictation_stopped = on_stop

    def request_dictation_stop(self) -> KernelResponse:
        if self._dictation_mode is None:
            return KernelResponse(False, "")
        return self._dictation_mode.stop()

    def attach_dictation_router(self, router: object) -> None:
        self._dictation_router = router

    def start_dictation(self, state: object) -> KernelResponse:
        from tusk.kernel.dictation_mode import AdapterDictationMode

        self._dictation_mode = AdapterDictationMode(state, self._dictation_router, self._log)
        if self._on_dictation_started is not None:
            self._on_dictation_started()
        self._report_mode(AppMode.DICTATION)
        return KernelResponse(True, "Dictation started.")

    def stop_dictation(self) -> None:
        self._dictation_mode = None
        if self._on_dictation_stopped is not None:
            self._on_dictation_stopped()
        self._report_mode(AppMode.DEFAULT)

    def set_coding_callbacks(
        self, on_start: Callable[[], None], on_stop: Callable[[], None]
    ) -> None:
        self._on_coding_started = on_start
        self._on_coding_stopped = on_stop

    def request_coding_stop(self) -> KernelResponse:
        if self._coding_mode is None:
            return KernelResponse(False, "")
        return self._coding_mode.stop()

    def attach_coding_router(self, router: object) -> None:
        self._coding_router = router

    @property
    def coding_active(self) -> bool:
        return self._coding_mode is not None

    def start_coding(self, state: object) -> KernelResponse:
        from tusk.kernel.coding_mode import AdapterCodingMode

        self._coding_mode = AdapterCodingMode(state, self._coding_router, self._log)
        if self._on_coding_started is not None:
            self._on_coding_started()
        return KernelResponse(True, "Coding started.")

    def stop_coding(self) -> None:
        self._coding_mode = None
        if self._on_coding_stopped is not None:
            self._on_coding_stopped()

    def get_llm_registry(self) -> object:
        return self._llm_registry
