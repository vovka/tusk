from tusk.kernel.registered_tool import RegisteredTool

__all__ = ["VisibleToolDefinitionBuilder"]


class VisibleToolDefinitionBuilder:
    def build(self, tools: list[RegisteredTool]) -> list[dict[str, object]]:
        return [self._definition(tool) for tool in tools]

    def _definition(self, tool: RegisteredTool) -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }
