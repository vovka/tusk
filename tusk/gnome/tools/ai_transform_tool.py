import time

from tusk.interfaces.agent_tool import AgentTool
from tusk.interfaces.clipboard_provider import ClipboardProvider
from tusk.interfaces.input_simulator import InputSimulator
from tusk.interfaces.llm_provider import LLMProvider
from tusk.schemas.tool_result import ToolResult

__all__ = ["AiTransformTool"]

_SYSTEM_PROMPT = (
    "Apply the user's instruction to the provided text. "
    "Return ONLY the transformed text, no explanation."
)

_CLIPBOARD_WAIT_SECONDS = 0.1
_MAX_TOKENS = 1024


class AiTransformTool(AgentTool):
    def __init__(
        self,
        simulator: InputSimulator,
        clipboard: ClipboardProvider,
        llm: LLMProvider,
    ) -> None:
        self._simulator = simulator
        self._clipboard = clipboard
        self._llm = llm

    @property
    def name(self) -> str:
        return "ai_transform"

    @property
    def description(self) -> str:
        return "Transform selected text using AI (summarize, translate, rewrite, etc.)"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"instruction": "<what_to_do_with_text>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        instruction = parameters["instruction"]
        text = self._copy_selected_text()
        if not text:
            return ToolResult(success=False, message="no text selected")
        result = self._transform(instruction, text)
        self._replace_selection(result)
        return ToolResult(success=True, message=f"transformed: {instruction}")

    def _copy_selected_text(self) -> str:
        self._simulator.press_keys("ctrl+c")
        time.sleep(_CLIPBOARD_WAIT_SECONDS)
        return self._clipboard.read()

    def _transform(self, instruction: str, text: str) -> str:
        user_message = f"Instruction: {instruction}\n\nText:\n{text}"
        return self._llm.complete(_SYSTEM_PROMPT, user_message, max_tokens=_MAX_TOKENS)

    def _replace_selection(self, text: str) -> None:
        self._simulator.press_keys("Delete")
        self._simulator.type_text(text)
