import json

from tusk.core.tool_registry import ToolRegistry
from tusk.interfaces.context_provider import ContextProvider
from tusk.interfaces.conversation_history import ConversationHistory
from tusk.interfaces.llm_provider import LLMProvider
from tusk.interfaces.log_printer import LogPrinter
from tusk.schemas.chat_message import ChatMessage
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
    'On your first response you may include an optional "reply" field with a brief natural-language '
    'acknowledgment of what you are about to do (e.g. {"tool":"press_keys","reply":"Sure, selecting all text.","keys":"ctrl+a"}). '
    'Use {"tool":"done","reply":"<confirmation>"} when the task is fully complete or needs no action. '
    'Use {"tool":"unknown","reason":"<why>"} only if the command cannot be mapped to any tool. '
    "Respond with JSON only."
)


class MainAgent:
    def __init__(
        self,
        llm_provider: LLMProvider,
        context_provider: ContextProvider,
        tool_registry: ToolRegistry,
        history: ConversationHistory,
        log_printer: LogPrinter,
    ) -> None:
        self._llm = llm_provider
        self._context = context_provider
        self._registry = tool_registry
        self._history = history
        self._log = log_printer

    def process_command(self, command: str) -> None:
        context = self._context.get_context()
        user_msg = ChatMessage("user", self._build_message(command, context))
        self._history.append(user_msg)
        prompt = self._build_system_prompt()
        self._log.log("LLM", f"→ {command!r}")
        self._run_tool_loop(prompt)

    def _run_tool_loop(self, prompt: str) -> None:
        for step in range(1, _MAX_STEPS + 1):
            messages = [m.to_dict() for m in self._history.get_messages()]
            raw = self._llm.complete_messages(prompt, messages)
            self._history.append(ChatMessage("assistant", raw))
            tool_call = self._parse_tool_call(raw)
            reply = tool_call.parameters.pop("reply", None)
            if reply:
                self._log.log("TUSK", reply)
            self._log_step(step, tool_call)
            if tool_call.tool_name in ("done", "unknown"):
                self._log_finish(step, tool_call)
                break
            result = self._execute(tool_call)
            self._log.log("TOOL", result.message)
            self._history.append(ChatMessage("user", f"Tool result: {result.message}"))
        else:
            self._log.log("AGENT", f"max steps reached ({_MAX_STEPS})")

    def _log_step(self, step: int, tool_call: ToolCall) -> None:
        params = ", ".join(f"{k}={v!r}" for k, v in tool_call.parameters.items())
        self._log.log("AGENT", f"step {step}: {tool_call.tool_name}({params})")

    def _log_finish(self, step: int, tool_call: ToolCall) -> None:
        if tool_call.tool_name == "unknown":
            self._log.log("AGENT", f"cannot handle: {tool_call.parameters.get('reason', '?')}")
            return
        self._log.log("AGENT", f"done ({step} steps)")

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
