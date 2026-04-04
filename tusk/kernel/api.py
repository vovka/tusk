from collections.abc import Callable

from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["KernelAPI"]


class KernelAPI:
    def __init__(
        self,
        command_mode: object,
        llm_registry: object,
        log: object | None = None,
    ) -> None:
        self._command_mode = command_mode
        self._llm_registry = llm_registry
        self._log = log
        self._dictation_mode = None
        self._dictation_router = None
        self._on_dictation_started: Callable[[], None] | None = None
        self._on_dictation_stopped: Callable[[], None] | None = None

    def submit(self, text: str) -> KernelResponse:
        if self._log is not None:
            self._log.log("KERNELINPUT", f"text={text!r}", "kernel-input")
        if self._dictation_mode is None:
            return self._command_mode.process_command(text)
        return self._dictation_mode.process_text(text)

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
        return KernelResponse(True, "Dictation started.")

    def stop_dictation(self) -> None:
        self._dictation_mode = None
        if self._on_dictation_stopped is not None:
            self._on_dictation_stopped()

    def get_llm_registry(self) -> object:
        return self._llm_registry
