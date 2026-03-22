from tusk.interfaces.agent_tool import AgentTool
from tusk.interfaces.input_simulator import InputSimulator
from tusk.schemas.tool_result import ToolResult

__all__ = ["MouseClickTool"]

_BUTTON_MAP = {"left": 1, "right": 3, "middle": 2}


class MouseClickTool(AgentTool):
    def __init__(self, simulator: InputSimulator) -> None:
        self._simulator = simulator

    @property
    def name(self) -> str:
        return "mouse_click"

    @property
    def description(self) -> str:
        return "Click the mouse at screen coordinates"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"x": "<x>", "y": "<y>", "button": "<left|right|middle>", "clicks": "<1|2|3>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        x = int(parameters["x"])
        y = int(parameters["y"])
        button = _BUTTON_MAP.get(parameters.get("button", "left"), 1)
        clicks = int(parameters.get("clicks", "1"))
        self._simulator.mouse_click(x, y, button, clicks)
        return ToolResult(success=True, message=f"clicked: ({x}, {y})")
