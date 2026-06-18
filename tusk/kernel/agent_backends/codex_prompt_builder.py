from tusk.kernel.agent_backends.agent_request import AgentRequest

__all__ = ["CodexPromptBuilder"]


class CodexPromptBuilder:
    def build(self, request: AgentRequest) -> str:
        return "\n\n".join(self._sections(request))

    def _sections(self, request: AgentRequest) -> list[str]:
        return [
            self._section("User command", request.user_text),
            self._section("Mode", request.mode),
            self._section("System context", self._context_value(request, "system_context")),
            self._section("Available tools", self._tools(request)),
            self._section("Working directory", request.working_directory),
            self._section("Safety policy", self._context_value(request, "safety_policy")),
            self._section("Expected response", self._schema_instruction(request)),
        ]

    def _section(self, title: str, value: object) -> str:
        return f"## {title}\n{self._text(value)}"

    def _context_value(self, request: AgentRequest, name: str) -> object:
        return request.context.get(name, "")

    def _tools(self, request: AgentRequest) -> object:
        return request.context.get("available_tools", "")

    def _schema_instruction(self, request: AgentRequest) -> object:
        return request.context.get("response_schema_instruction", "")

    def _text(self, value: object) -> str:
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return str(value)
