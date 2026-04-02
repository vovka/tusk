from tusk.kernel.dictation_state import DictationState
from tusk.shared.schemas.tool_result import ToolResult

__all__ = ["StartDictationTool"]


class StartDictationTool:
    source = "kernel"
    name = "start_dictation"
    description = "Start adapter-driven dictation mode"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, tool_registry: object, controller: object, adapter_manager: object) -> None:
        self._registry = tool_registry
        self._controller = controller
        self._manager = adapter_manager

    def execute(self, parameters: dict) -> ToolResult:
        try:
            result = self._registry.get("dictation.start_dictation").execute({})
        except KeyError:
            return ToolResult(False, "dictation adapter is not available")
        if not result.success or result.data is None:
            return ToolResult(False, result.message)
        state = DictationState("dictation", result.data["session_id"], self._manager.primary_desktop_source())
        response = self._controller.start_dictation(state)
        return ToolResult(response.handled, response.reply, result.data)
