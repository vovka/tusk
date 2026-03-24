from tusk.interfaces.agent_tool import AgentTool
from tusk.interfaces.input_simulator import InputSimulator
from tusk.schemas.tool_result import ToolResult

__all__ = ["MouseMoveTool"]


class MouseMoveTool(AgentTool):
    def __init__(self, simulator: InputSimulator) -> None:
        self._simulator = simulator

    @property
    def name(self) -> str:
        return "mouse_move"

    @property
    def description(self) -> str:
        return "Move the mouse cursor to screen coordinates"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"x": "<x>", "y": "<y>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        x = int(parameters["x"])
        y = int(parameters["y"])
        self._simulator.mouse_move(x, y)
        return ToolResult(success=True, message=f"moved to: ({x}, {y})")
