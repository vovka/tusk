from collections.abc import Callable

from tusk.kernel.mode_slot import ModeSlot
from tusk.kernel.submit_status_reporter import SubmitStatusReporter
from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["KernelAPI"]


class KernelAPI:
    def __init__(
        self, command_mode: object, llm_registry: object, log: object | None = None,
        reporter: object | None = None, interrupt_token: object | None = None,
    ) -> None:
        self._command_mode = command_mode
        self._llm_registry = llm_registry
        self._log = log
        self._reporter = reporter
        self._interrupt_token = interrupt_token
        self._submit_reporter = SubmitStatusReporter(reporter) if reporter is not None else None
        self._dictation = ModeSlot("DICTATION", "Dictation started.")
        self._coding = ModeSlot("CODING", "Coding started.")

    def request_interrupt(self) -> None:
        if self._interrupt_token is not None:
            self._interrupt_token.interrupt()

    @property
    def interrupt_token(self) -> object | None:
        return self._interrupt_token

    def submit(self, text: str) -> KernelResponse:
        self._log_input(text)
        if self._submit_reporter is None:
            return self._route(text)
        return self._submit_reporter.run(text, self._route)

    def _log_input(self, text: str) -> None:
        if self._log is not None:
            self._log.log("KERNELINPUT", f"text={text!r}", "kernel-input")

    def _route(self, text: str) -> KernelResponse:
        if self._coding.active:
            return self._coding.process_text(text)
        if self._dictation.active:
            return self._dictation.process_text(text)
        return self._command_mode.process_command(text)

    def _report_mode(self, mode: AppMode) -> None:
        if self._reporter is not None:
            self._reporter.set_mode(mode)

    def set_dictation_callbacks(self, on_start: Callable[[], None], on_stop: Callable[[], None]) -> None:
        self._dictation.set_callbacks(on_start, on_stop)

    def request_dictation_stop(self) -> KernelResponse:
        return self._dictation.request_stop()

    def attach_dictation_router(self, router: object) -> None:
        self._dictation.attach_router(router)

    def start_dictation(self, state: object) -> KernelResponse:
        response = self._dictation.start(state, self._log)
        self._report_mode(AppMode.DICTATION)
        return response

    def stop_dictation(self) -> None:
        self._dictation.stop()
        self._report_mode(AppMode.DEFAULT)

    def set_coding_callbacks(self, on_start: Callable[[], None], on_stop: Callable[[], None]) -> None:
        self._coding.set_callbacks(on_start, on_stop)

    def request_coding_stop(self) -> KernelResponse:
        return self._coding.request_stop()

    def attach_coding_router(self, router: object) -> None:
        self._coding.attach_router(router)

    @property
    def coding_active(self) -> bool:
        return self._coding.active

    def start_coding(self, state: object) -> KernelResponse:
        return self._coding.start(state, self._log)

    def stop_coding(self) -> None:
        self._coding.stop()

    def get_llm_registry(self) -> object:
        return self._llm_registry
