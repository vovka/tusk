import json

from tusk.core.tool_registry import ToolRegistry
from tusk.interfaces.context_provider import ContextProvider
from tusk.interfaces.llm_provider import LLMProvider
from tusk.schemas.desktop_context import DesktopContext
from tusk.schemas.tool_call import ToolCall
from tusk.schemas.tool_result import ToolResult

__all__ = ["MainAgent"]

_MAX_STEPS = 10

_SYSTEM_PROMPT_PREFIX = (
    "You are TUSK, a desktop voice assistant. "
    "Given a user command and desktop context, call tools one at a time to complete it. "
    "Available tools:\n"
)

_SYSTEM_PROMPT_SUFFIX = (
    '\nRespond with JSON matching one tool schema per message. '
    'Use {"tool":"done"} when the task is fully complete or needs no action. '
    'Use {"tool":"unknown","reason":"<why>"} only if the command cannot be mapped to any tool. '
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

    def process_command(self, command: str) -> None:
        context = self._context.get_context()
        messages = [{"role": "user", "content": self._build_message(command, context)}]
        prompt = self._build_system_prompt()
        for _ in range(_MAX_STEPS):
            raw = self._llm.complete_messages(prompt, messages)
            print(f"[LLM:agent] {raw!r}")
            messages.append({"role": "assistant", "content": raw})
            tool_call = self._parse_tool_call(raw)
            if tool_call.tool_name in ("done", "unknown"):
                if tool_call.tool_name == "unknown":
                    print(f"[AGENT] cannot handle: {tool_call.parameters.get('reason', '?')}")
                break
            result = self._execute(tool_call)
            print(f"[TOOL] {result.message}")
            messages.append({"role": "user", "content": f"Tool result: {result.message}"})
        else:
            print("[AGENT] max steps reached")

    def _execute(self, tool_call: ToolCall) -> ToolResult:
        try:
            return self._registry.get(tool_call.tool_name).execute(tool_call.parameters)
        except KeyError:
            return ToolResult(success=False, message=f"unknown tool: {tool_call.tool_name}")

    def _build_system_prompt(self) -> str:
        return _SYSTEM_PROMPT_PREFIX + self._registry.build_schema_text() + _SYSTEM_PROMPT_SUFFIX

    def _build_message(self, command: str, ctx: DesktopContext) -> str:
        windows = "\n".join(
            f"  {w.title} [{w.width}x{w.height} at {w.x},{w.y}]"
            for w in ctx.open_windows
        )
        apps = "\n".join(f"{a.name} → {a.exec_cmd}" for a in ctx.available_applications)
        return (
            f"Command: {command}\n"
            f"Active window: {ctx.active_window_title}\n"
            f"Open windows:\n{windows or '  none'}\n"
            f"Available apps (name → exec_cmd):\n{apps or 'none'}"
        )

    def _parse_tool_call(self, raw: str) -> ToolCall:
        try:
            data = json.loads(raw.strip())
            tool_name = data.pop("tool")
            return ToolCall(tool_name=tool_name, parameters=data)
        except Exception:
            return ToolCall(tool_name="done", parameters={})
