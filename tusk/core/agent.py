import json

from tusk.core.tool_registry import ToolRegistry
from tusk.interfaces.context_provider import ContextProvider
from tusk.interfaces.llm_provider import LLMProvider
from tusk.schemas.desktop_context import DesktopContext
from tusk.schemas.tool_call import ToolCall

__all__ = ["MainAgent"]

_SYSTEM_PROMPT_PREFIX = (
    "You are TUSK, a desktop voice assistant. "
    "Given a user command and desktop context, output ONLY valid JSON "
    "matching one of the available tools:\n"
)

_SYSTEM_PROMPT_SUFFIX = (
    '\nUse {"tool":"unknown","reason":"<why>"} if the command '
    "is too garbled or cannot be mapped to a known tool. "
    "Respond with JSON only, no explanation."
)


class MainAgent:
    def __init__(
        self,
        llm_provider: LLMProvider,
        context_provider: ContextProvider,
        tool_registry: ToolRegistry,
    ) -> None:
        self._llm = llm_provider
        self._context = context_provider
        self._registry = tool_registry

    def process_command(self, command: str) -> ToolCall:
        context = self._context.get_context()
        user_message = self._build_message(command, context)
        prompt = self._build_system_prompt()
        raw = self._llm.complete(prompt, user_message)
        print(f"[LLM:agent] {raw!r}")
        return self._parse_tool_call(raw)

    def _build_system_prompt(self) -> str:
        schema_text = self._registry.build_schema_text()
        return _SYSTEM_PROMPT_PREFIX + schema_text + _SYSTEM_PROMPT_SUFFIX

    def _build_message(self, command: str, ctx: DesktopContext) -> str:
        windows = [w.title for w in ctx.open_windows]
        apps = "\n".join(
            f"{a.name} → {a.exec_cmd}" for a in ctx.available_applications
        )
        return (
            f"Command: {command}\n"
            f"Active window: {ctx.active_window_title}\n"
            f"Open windows: {', '.join(windows) or 'none'}\n"
            f"Available apps (name → exec_cmd):\n{apps or 'none'}"
        )

    def _parse_tool_call(self, raw: str) -> ToolCall:
        data = json.loads(raw.strip())
        tool_name = data.pop("tool")
        return ToolCall(tool_name=tool_name, parameters=data)
