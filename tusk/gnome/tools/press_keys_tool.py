from tusk.interfaces.agent_tool import AgentTool
from tusk.interfaces.input_simulator import InputSimulator
from tusk.schemas.tool_result import ToolResult

__all__ = ["PressKeysTool"]


class PressKeysTool(AgentTool):
    def __init__(self, simulator: InputSimulator) -> None:
        self._simulator = simulator

    @property
    def name(self) -> str:
        return "press_keys"

    @property
    def description(self) -> str:
        return "Press a keyboard shortcut or key combination"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"keys": "<key_combination>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        keys = parameters["keys"]
        self._simulator.press_keys(keys)
        return ToolResult(success=True, message=f"pressed: {keys}")
