from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.logging.interfaces.log_printer import LogPrinter

__all__ = ["AdapterMode"]


class AdapterMode:
    """Routes mode text through an adapter-backed router (dictation, coding)."""

    def __init__(self, state: object, router: object, log_printer: LogPrinter | None, log_tag: str) -> None:
        self._state = state
        self._router = router
        self._log = log_printer
        self._tag = log_tag

    @property
    def state(self) -> object:
        return self._state

    def process_text(self, text: str) -> KernelResponse:
        result = self._router.process(self._state, text)
        self._log.log(self._tag, result.reply or "updated")
        return result

    def stop(self) -> KernelResponse:
        result = self._router.stop(self._state)
        self._log.log(self._tag, result.reply or "stopped")
        return result
