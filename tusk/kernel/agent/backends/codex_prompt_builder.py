from tusk.kernel.agent.backends.agent_request import AgentRequest

__all__ = ["CodexPromptBuilder"]

DEFAULT_SYSTEM_CONTEXT = (
    "You are the action backend of TUSK, a voice assistant controlling the user's Linux/GNOME desktop.\n"
    "You run in a headless container: your own shell cannot open or see the user's GUI applications.\n"
    "Perform every desktop action (launch, focus, type, clipboard, mouse) through the gnome MCP tools only.\n"
    "Ground yourself with get_desktop_context or list_windows before acting.\n"
    "Open applications with launch_application and confirm focus via get_active_window before type_text.\n"
    "Your reply is spoken aloud: answer in one short sentence."
)


class CodexPromptBuilder:
    def build(self, request: AgentRequest) -> str:
        sections = [self._section(title, value) for title, value in self._fields(request)]
        return "\n\n".join(section for section in sections if section)

    def _fields(self, request: AgentRequest) -> list[tuple[str, object]]:
        return [
            ("System context", request.context.get("system_context") or DEFAULT_SYSTEM_CONTEXT),
            ("User command", request.user_text),
            ("Mode", request.mode),
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
