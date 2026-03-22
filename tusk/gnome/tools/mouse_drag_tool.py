from tusk.interfaces.agent_tool import AgentTool
from tusk.interfaces.input_simulator import InputSimulator
from tusk.schemas.tool_result import ToolResult

__all__ = ["MouseDragTool"]


class MouseDragTool(AgentTool):
    def __init__(self, simulator: InputSimulator) -> None:
        self._simulator = simulator

    @property
    def name(self) -> str:
        return "mouse_drag"

    @property
    def description(self) -> str:
        return "Drag the mouse from one position to another"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"from_x": "<x>", "from_y": "<y>", "to_x": "<x>", "to_y": "<y>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        from_x = int(parameters["from_x"])
        from_y = int(parameters["from_y"])
        to_x = int(parameters["to_x"])
        to_y = int(parameters["to_y"])
        self._simulator.mouse_drag(from_x, from_y, to_x, to_y, button=1)
        return ToolResult(success=True, message=f"dragged: ({from_x},{from_y}) → ({to_x},{to_y})")
