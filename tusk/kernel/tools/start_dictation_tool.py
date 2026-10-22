from tusk.kernel.modes.mode_state import ModeState
from tusk.kernel.modes.mode_slot import ModeSlot
from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.kernel.tools.adapter_manager import AdapterManager
from tusk.kernel.tools.tool_registry import ToolRegistry

__all__ = ["StartDictationTool"]


class StartDictationTool:
    source = "kernel"
    name = "start_dictation"
    description = "Start adapter-driven dictation mode"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, tool_registry: ToolRegistry, slot: ModeSlot, adapter_manager: AdapterManager) -> None:
        self._registry = tool_registry
        self._slot = slot
        self._manager = adapter_manager

    def execute(self, parameters: dict) -> ToolResult:
        try:
            result = self._registry.get("dictation.start_dictation").execute({})
        except KeyError:
            return ToolResult(False, "dictation adapter is not available")
        if not result.success or result.data is None:
            return ToolResult(False, result.message)
        state = ModeState("dictation", result.data["session_id"], self._manager.primary_desktop_source())
        response = self._slot.start(state)
        return ToolResult(response.handled, response.reply, result.data)
