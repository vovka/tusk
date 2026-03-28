__all__ = ["ToolPromptBuilder"]


class ToolPromptBuilder:
    def build(self, tools: list[object]) -> str:
        return "\n".join(["Available tool names:", *[self._line(tool) for tool in tools]])

    def _line(self, tool: object) -> str:
        return f"- {tool.name}: {tool.description}"
