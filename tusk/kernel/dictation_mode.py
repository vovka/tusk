from tusk.kernel.dictation_state import DictationState
from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.schemas.kernel_response import KernelResponse

__all__ = ["AdapterDictationMode"]


class AdapterDictationMode:
    def __init__(self, state: DictationState, router: object, log_printer: LogPrinter) -> None:
        self._state = state
        self._router = router
        self._log = log_printer

    @property
    def state(self) -> DictationState:
        return self._state

    def process_text(self, text: str) -> KernelResponse:
        result = self._router.process(self._state, text)
        self._log.log("DICTATION", result.reply or "updated")
        return result
