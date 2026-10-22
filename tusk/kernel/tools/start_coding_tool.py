from tusk.kernel.modes.mode_state import ModeState
from tusk.kernel.modes.mode_slot import ModeSlot
from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.kernel.core.adapter_manager import AdapterManager
from tusk.kernel.interfaces.editor_driver import EditorDriver
from tusk.kernel.tools.tool_registry import ToolRegistry

__all__ = ["StartCodingTool"]


class StartCodingTool:
    source = "kernel"
    name = "start_coding"
    description = "Start pair-coding mode (coding session, pair programming): spoken code edits go to the focused editor."
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, tool_registry: ToolRegistry, slot: ModeSlot, adapter_manager: AdapterManager, driver: EditorDriver) -> None:
        self._registry = tool_registry
        self._slot = slot
        self._manager = adapter_manager
        self._driver = driver

    def execute(self, parameters: dict) -> ToolResult:
        if self._slot.active:
            return ToolResult(True, "Already in pair-coding mode.")
        try:
            result = self._start_session()
        except KeyError:
            return ToolResult(False, "coding adapter is not available")
        if not result.success or result.data is None:
            return ToolResult(False, result.message)
        return self._begin(result)

    def _start_session(self) -> ToolResult:
        initial_buffer = self._driver.read_buffer()
        return self._registry.get("coding.start_coding_session").execute({"initial_buffer": initial_buffer})

    def _begin(self, result: ToolResult) -> ToolResult:
        state = ModeState("coding", result.data["session_id"], self._manager.primary_desktop_source())
        response = self._slot.start(state)
        return ToolResult(response.handled, response.reply, result.data)
