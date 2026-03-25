from tusk.kernel.dictation_mode import DictationState
from tusk.kernel.schemas.kernel_response import KernelResponse
from tusk.kernel.schemas.tool_result import ToolResult

__all__ = ["DictationRouter", "StartDictationTool", "SwitchModelTool"]


class SwitchModelTool:
    source = "kernel"
    name = "switch_model"
    description = "Switch LLM provider/model for a slot"
    input_schema = {"type": "object", "properties": {"slot": {"type": "string"}, "provider": {"type": "string"}, "model": {"type": "string"}}, "required": ["slot", "provider", "model"]}

    def __init__(self, llm_registry: object) -> None:
        self._registry = llm_registry

    def execute(self, parameters: dict) -> ToolResult:
        try:
            message = self._registry.swap(parameters["slot"], parameters["provider"], parameters["model"])
            return ToolResult(True, message)
        except (KeyError, ValueError) as exc:
            return ToolResult(False, str(exc))


class StartDictationTool:
    source = "kernel"
    name = "start_dictation"
    description = "Start adapter-driven dictation mode"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, tool_registry: object, pipeline: object, adapter_manager: object) -> None:
        self._registry = tool_registry
        self._pipeline = pipeline
        self._manager = adapter_manager

    def execute(self, parameters: dict) -> ToolResult:
        try:
            result = self._registry.get("dictation.start_dictation").execute({})
        except KeyError:
            return ToolResult(False, "dictation adapter is not available")
        if not result.success or result.data is None:
            return ToolResult(False, result.message)
        state = DictationState("dictation", result.data["session_id"], self._manager.primary_desktop_source())
        response = self._pipeline.start_dictation(state)
        return ToolResult(response.handled, response.reply, result.data)


class DictationRouter:
    def __init__(self, tool_registry: object, pipeline: object) -> None:
        self._registry = tool_registry
        self._pipeline = pipeline

    def process(self, state: object, text: str) -> KernelResponse:
        result = self._registry.get(f"{state.adapter_name}.process_segment").execute(
            {"session_id": state.session_id, "text": text},
        )
        if not result.success or result.data is None:
            return KernelResponse(False, result.message)
        self._apply_edit(state.desktop_source, result.data)
        if result.data.get("should_stop"):
            self._registry.get(f"{state.adapter_name}.stop_dictation").execute({"session_id": state.session_id})
            self._pipeline.stop_dictation()
            return KernelResponse(True, "Dictation stopped.")
        return KernelResponse(True, result.message)

    def _apply_edit(self, desktop_source: str, data: dict) -> None:
        operation = data.get("operation")
        if operation == "insert":
            self._registry.get(f"{desktop_source}.type_text").execute({"text": data.get("text", "")})
        if operation == "replace":
            self._registry.get(f"{desktop_source}.replace_recent_text").execute(
                {"text": data.get("text", ""), "replace_chars": str(data.get("replace_chars", 0))},
            )
