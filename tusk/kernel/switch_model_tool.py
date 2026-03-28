from tusk.kernel.schemas.tool_result import ToolResult

__all__ = ["SwitchModelTool"]


class SwitchModelTool:
    source = "kernel"
    name = "switch_model"
    description = "Switch LLM provider/model for a slot"
    input_schema = {
        "type": "object",
        "properties": {
            "slot": {"type": "string"},
            "provider": {"type": "string"},
            "model": {"type": "string"},
        },
        "required": ["slot", "provider", "model"],
    }

    def __init__(self, llm_registry: object) -> None:
        self._registry = llm_registry

    def execute(self, parameters: dict) -> ToolResult:
        try:
            message = self._registry.swap(parameters["slot"], parameters["provider"], parameters["model"])
        except (KeyError, ValueError) as exc:
            return ToolResult(False, str(exc))
        return ToolResult(True, message)
