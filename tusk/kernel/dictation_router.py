from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.schemas.kernel_response import KernelResponse

__all__ = ["DictationRouter"]


class DictationRouter:
    def __init__(self, tool_registry: object, pipeline: object, log_printer: object) -> None:
        self._registry = tool_registry
        self._pipeline = pipeline
        self._log = log_printer

    def process(self, state: object, text: str) -> KernelResponse:
        result = self._segment_result(state, text)
        self._log.log("DICTATION", f"segment={text!r}")
        if not result.success or result.data is None:
            return KernelResponse(False, result.message)
        self._log_active_window(state.desktop_source)
        apply_result = self._apply_edit(state.desktop_source, result.data)
        if not apply_result.success:
            self._log.log("DICTATION", f"apply failed via {state.desktop_source}: {apply_result.message}")
            return KernelResponse(False, apply_result.message)
        return KernelResponse(True, result.message)

    def stop(self, state: object) -> KernelResponse:
        self._registry.get(f"{state.adapter_name}.stop_dictation").execute({"session_id": state.session_id})
        self._pipeline.stop_dictation()
        return KernelResponse(True, "Dictation stopped.")

    def _segment_result(self, state: object, text: str) -> object:
        name = f"{state.adapter_name}.process_segment"
        return self._registry.get(name).execute({"session_id": state.session_id, "text": text})

    def _apply_edit(self, desktop_source: str, data: dict) -> ToolResult:
        self._log.log("DICTATION", f"apply {data.get('operation', 'noop')} via {desktop_source}")
        if data.get("operation") == "insert":
            return self._registry.get(f"{desktop_source}.type_text").execute({"text": data.get("text", "")})
        if data.get("operation") == "replace":
            return self._registry.get(f"{desktop_source}.replace_recent_text").execute(self._replace_args(data))
        return ToolResult(True, "no edit")

    def _replace_args(self, data: dict) -> dict:
        return {"text": data.get("text", ""), "replace_chars": str(data.get("replace_chars", 0))}

    def _log_active_window(self, desktop_source: str) -> None:
        name = f"{desktop_source}.get_active_window"
        try:
            result = self._registry.get(name).execute({})
        except KeyError:
            return
        if result.success and result.message:
            self._log.log("DICTATION", result.message)
