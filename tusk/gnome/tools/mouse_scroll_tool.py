from tusk.interfaces.agent_tool import AgentTool
from tusk.interfaces.input_simulator import InputSimulator
from tusk.schemas.tool_result import ToolResult

__all__ = ["MouseScrollTool"]


class MouseScrollTool(AgentTool):
    def __init__(self, simulator: InputSimulator) -> None:
        self._simulator = simulator

    @property
    def name(self) -> str:
        return "mouse_scroll"

    @property
    def description(self) -> str:
        return "Scroll the mouse wheel up or down"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"direction": "<up|down>", "clicks": "<amount>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        direction = parameters.get("direction", "down")
        clicks = int(parameters.get("clicks", "3"))
        self._simulator.mouse_scroll(direction, clicks)
        return ToolResult(success=True, message=f"scrolled {direction} {clicks}")
