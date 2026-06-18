from tusk.kernel.agent_backends.agent_request import AgentRequest

__all__ = ["CodexPromptBuilder"]


class CodexPromptBuilder:
    def build(self, request: AgentRequest) -> str:
        sections = [self._section(title, value) for title, value in self._fields(request)]
        return "\n\n".join(section for section in sections if section)

    def _fields(self, request: AgentRequest) -> list[tuple[str, object]]:
        return [
            ("User command", request.user_text),
            ("Mode", request.mode),
            ("System context", request.context.get("system_context")),
            ("Available tools", request.context.get("available_tools")),
            ("Working directory", request.working_directory),
            ("Safety policy", request.context.get("safety_policy")),
            ("Expected response", request.context.get("response_schema_instruction")),
        ]

    def _section(self, title: str, value: object) -> str:
        text = self._text(value).strip()
        if not text:
            return ""
        return f"## {title}\n{text}"

    def _text(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return "\n".join(str(item) for item in value if item is not None)
        return str(value)
