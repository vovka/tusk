from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["KernelAPI"]


class KernelAPI:
    def __init__(self, command_mode: object, llm_registry: object, log: object | None = None) -> None:
        self._command_mode = command_mode
        self._llm_registry = llm_registry
        self._log = log
        self._dictation_mode = None
        self._dictation_router = None

    def submit(self, text: str) -> KernelResponse:
        if self._dictation_mode is None:
            return self._command_mode.process_command(text)
        return self._submit_dictation(text)

    def attach_dictation_router(self, router: object) -> None:
        self._dictation_router = router

    def start_dictation(self, state: object) -> KernelResponse:
        from tusk.kernel.dictation_mode import AdapterDictationMode

        self._dictation_mode = AdapterDictationMode(state, self._dictation_router, self._log)
        return KernelResponse(True, "Dictation started.")

    def stop_dictation(self) -> None:
        self._dictation_mode = None

    def get_llm_registry(self) -> object:
        return self._llm_registry

    def _submit_dictation(self, text: str) -> KernelResponse:
        if _is_stop_request(text):
            return self._dictation_mode.stop()
        return self._dictation_mode.process_text(text)


def _is_stop_request(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return normalized in {"stop dictation", "stop dictation mode", "end dictation"}
