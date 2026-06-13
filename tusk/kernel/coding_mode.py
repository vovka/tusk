from tusk.kernel.coding_state import CodingState
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["AdapterCodingMode"]


class AdapterCodingMode:
    def __init__(self, state: CodingState, router: object, log_printer: LogPrinter) -> None:
        self._state = state
        self._router = router
        self._log = log_printer

    @property
    def state(self) -> CodingState:
        return self._state

    def process_text(self, text: str) -> KernelResponse:
        result = self._router.process(self._state, text)
        self._log.log("CODING", result.reply or "updated")
        return result

    def stop(self) -> KernelResponse:
        result = self._router.stop(self._state)
        self._log.log("CODING", result.reply or "stopped")
        return result
