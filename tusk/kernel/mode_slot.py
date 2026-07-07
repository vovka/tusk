from collections.abc import Callable

from tusk.kernel.adapter_mode import AdapterMode
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["ModeSlot"]


class ModeSlot:
    """Holds one switchable kernel mode (dictation, coding) and its wiring."""

    def __init__(self, log_tag: str, start_reply: str) -> None:
        self._log_tag = log_tag
        self._start_reply = start_reply
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
        assert self._mode is not None
        return self._mode.process_text(text)

    def request_stop(self) -> KernelResponse:
        if self._mode is None:
            return KernelResponse(False, "")
        return self._mode.stop()

    def start(self, state: object, log: object) -> KernelResponse:
        self._mode = AdapterMode(state, self._router, log, self._log_tag)
        if self._on_started is not None:
            self._on_started()
        return KernelResponse(True, self._start_reply)

    def stop(self) -> None:
        self._mode = None
        if self._on_stopped is not None:
            self._on_stopped()
