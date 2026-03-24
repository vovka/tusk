import json

from tusk.core.agent_prompts import MAX_STEPS, SYSTEM_PROMPT_PREFIX, SYSTEM_PROMPT_SUFFIX, TERMINAL_TOOLS
from tusk.core.tool_registry import ToolRegistry
from tusk.interfaces.context_provider import ContextProvider
from tusk.interfaces.conversation_history import ConversationHistory
from tusk.interfaces.conversation_logger import ConversationLogger
from tusk.interfaces.llm_provider import LLMProvider
from tusk.interfaces.log_printer import LogPrinter
from tusk.interfaces.message_compactor import MessageCompactor
from tusk.schemas.chat_message import ChatMessage
from tusk.schemas.desktop_context import DesktopContext
from tusk.schemas.tool_call import ToolCall
from tusk.schemas.tool_result import ToolResult

__all__ = ["MainAgent"]


class MainAgent:
    def __init__(
        self,
        llm_provider: LLMProvider,
        context_provider: ContextProvider,
        tool_registry: ToolRegistry,
        history: ConversationHistory,
        log_printer: LogPrinter,
        compactor: MessageCompactor | None = None,
        logger: ConversationLogger | None = None,
    ) -> None:
        self._llm = llm_provider
        self._context = context_provider
        self._registry = tool_registry
        self._history = history
        self._log = log_printer
        self._compactor = compactor
        self._logger = logger

    def process_command(self, command: str) -> None:
        context = self._context.get_context()
        user_msg = ChatMessage("user", self._build_message(command, context))
        self._history.append(user_msg)
        prompt = self._build_system_prompt()
        self._log.log("LLM", f"[{self._llm.label}] → {command!r}")
        self._run_tool_loop(prompt)

    def _run_tool_loop(self, prompt: str) -> None:
        for step in range(1, MAX_STEPS + 1):
            tool_call = self._run_step(prompt)
            self._log_step(step, tool_call)
            if tool_call.tool_name in TERMINAL_TOOLS:
                self._log_finish(step, tool_call)
                break
            result = self._execute(tool_call)
            self._log.log("TOOL", result.message)
            self._append(ChatMessage("user", f"Tool result: {result.message}"))
        else:
            self._log.log("AGENT", f"max steps reached ({MAX_STEPS})")

    def _run_step(self, prompt: str) -> ToolCall:
        messages = [m.to_dict() for m in self._history.get_messages()]
        raw = self._llm.complete_messages(prompt, messages)
        self._append(ChatMessage("assistant", raw))
        tool_call = self._parse_tool_call(raw)
        reply = tool_call.parameters.pop("reply", None)
        if reply:
            self._log.log("TUSK", reply)
        return tool_call

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

    def _append(self, message: ChatMessage) -> None:
        if self._logger:
            self._logger.log_message(message)
        compacted = self._compactor.compact(message) if self._compactor else message
        self._history.append(compacted)

    def _build_system_prompt(self) -> str:
        return SYSTEM_PROMPT_PREFIX + self._registry.build_schema_text() + SYSTEM_PROMPT_SUFFIX

    def _build_message(self, command: str, ctx: DesktopContext) -> str:
        windows = _format_windows(ctx)
        apps = _format_apps(ctx)
        return f"Command: {command}\nActive window: {ctx.active_window_title}\n{windows}\n{apps}"

    def _parse_tool_call(self, raw: str) -> ToolCall:
        try:
            data = json.loads(raw.strip())
            return ToolCall(tool_name=data.pop("tool"), parameters=data)
        except Exception:
            return ToolCall(tool_name="done", parameters={})


def _format_windows(ctx: DesktopContext) -> str:
    lines = "\n".join(f"  {w.title} [{w.width}x{w.height} at {w.x},{w.y}]" for w in ctx.open_windows)
    return f"Open windows:\n{lines or '  none'}"


def _format_apps(ctx: DesktopContext) -> str:
    lines = "\n".join(f"{a.name} → {a.exec_cmd}" for a in ctx.available_applications)
    return f"Available apps (name → exec_cmd):\n{lines or 'none'}"
