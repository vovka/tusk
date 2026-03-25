from tusk.kernel.schemas.kernel_response import KernelResponse

__all__ = ["DictationRouter"]


class DictationRouter:
    def __init__(self, tool_registry: object, pipeline: object) -> None:
        self._registry = tool_registry
        self._pipeline = pipeline

    def process(self, state: object, text: str) -> KernelResponse:
        result = self._segment_result(state, text)
        if not result.success or result.data is None:
            return KernelResponse(False, result.message)
        self._apply_edit(state.desktop_source, result.data)
        return self._build_response(state, result)

    def _segment_result(self, state: object, text: str) -> object:
        name = f"{state.adapter_name}.process_segment"
        return self._registry.get(name).execute({"session_id": state.session_id, "text": text})

    def _apply_edit(self, desktop_source: str, data: dict) -> None:
        if data.get("operation") == "insert":
            self._registry.get(f"{desktop_source}.type_text").execute({"text": data.get("text", "")})
        if data.get("operation") == "replace":
            self._registry.get(f"{desktop_source}.replace_recent_text").execute(self._replace_args(data))

    def _replace_args(self, data: dict) -> dict:
        return {"text": data.get("text", ""), "replace_chars": str(data.get("replace_chars", 0))}

    def _build_response(self, state: object, result: object) -> KernelResponse:
        if not result.data.get("should_stop"):
            return KernelResponse(True, result.message)
        self._registry.get(f"{state.adapter_name}.stop_dictation").execute({"session_id": state.session_id})
        self._pipeline.stop_dictation()
        return KernelResponse(True, "Dictation stopped.")
