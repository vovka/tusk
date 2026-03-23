from tusk.core.llm_registry import LLMRegistry
from tusk.interfaces.agent_tool import AgentTool
from tusk.schemas.tool_result import ToolResult

__all__ = ["SwitchModelTool"]


class SwitchModelTool(AgentTool):
    def __init__(self, llm_registry: LLMRegistry) -> None:
        self._registry = llm_registry

    @property
    def name(self) -> str:
        return "switch_model"

    @property
    def description(self) -> str:
        slots = ", ".join(self._registry.slot_names)
        return f"Switch LLM provider/model for a slot ({slots})"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {
            "slot": "<agent|utility|gatekeeper>",
            "provider": "<groq|openrouter>",
            "model": "<model_id>",
        }

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        try:
            result = self._registry.swap(
                parameters["slot"],
                parameters["provider"],
                parameters["model"],
            )
            return ToolResult(success=True, message=result)
        except (KeyError, ValueError) as exc:
            return ToolResult(success=False, message=str(exc))
