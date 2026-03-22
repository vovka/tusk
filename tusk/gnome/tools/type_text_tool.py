from tusk.interfaces.agent_tool import AgentTool
from tusk.interfaces.input_simulator import InputSimulator
from tusk.schemas.tool_result import ToolResult

__all__ = ["TypeTextTool"]


class TypeTextTool(AgentTool):
    def __init__(self, simulator: InputSimulator) -> None:
        self._simulator = simulator

    @property
    def name(self) -> str:
        return "type_text"

    @property
    def description(self) -> str:
        return "Type text as keyboard input into the active window"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"text": "<text_to_type>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        text = parameters["text"]
        self._simulator.type_text(text)
        return ToolResult(success=True, message=f"typed: {text[:50]}")
