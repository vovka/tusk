import json

from tusk.kernel.interfaces.agent import Agent
from tusk.kernel.interfaces.conversation_history import ConversationHistory
from tusk.kernel.interfaces.llm_provider import LLMProvider
from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.schemas.chat_message import ChatMessage
from tusk.kernel.schemas.desktop_context import DesktopContext
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry

__all__ = ["MainAgent"]

_MAX_STEPS = 10
_MAX_WINDOWS = 12
_MAX_APPS = 40
_MAX_APP_NAME_LENGTH = 40
_SYSTEM_PROMPT = "\n".join([
    "You are TUSK, a desktop assistant.",
    "Use exactly one tool per response.",
    'Respond with JSON only.',
    'Every response must include "tool" and "reply".',
    'Use {"tool":"done","reply":"<final response>"} when no tool is needed.',
    'Use {"tool":"unknown","reply":"<brief response>","reason":"<why>"} only when the request cannot be handled.',
    'When calling a tool, return a flat JSON object like {"tool":"gnome.launch_application","reply":"Opening gedit.","application_name":"gedit"}.',
    "Available tools:",
])


class MainAgent(Agent):
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        history: ConversationHistory,
        context_provider: object,
        log_printer: LogPrinter,
    ) -> None:
        self._llm = llm_provider
        self._registry = tool_registry
        self._history = history
        self._context = context_provider
        self._log = log_printer

    def process_command(self, command: str) -> str:
        context = self._context.get_context()
        prompt = self._build_system_prompt()
        reply = self._run_tool_loop(
            prompt,
            self._build_context_message(context),
            self._build_command_history(command),
        )
        self._remember_exchange(command, reply)
        return reply

    def _run_tool_loop(
        self,
        prompt: str,
        context_message: str,
        command_history: list[dict[str, str]],
    ) -> str:
        reply = ""
        messages = [ChatMessage("user", context_message).to_dict(), *command_history]
        for step in range(1, _MAX_STEPS + 1):
            raw = self._llm.complete_messages(prompt, messages)
            self._log.log("LLM", f"[{self._llm.label}] agent → {raw!r}")
            messages.append(ChatMessage("assistant", raw).to_dict())
            tool_call = self._parse_tool_call(raw)
            reply = tool_call.parameters.pop("reply", reply)
            if reply:
                self._log.log("TUSK", reply)
            if tool_call.tool_name in ("done", "unknown"):
                if tool_call.tool_name == "unknown":
                    reason = tool_call.parameters.get("reason", "unknown reason")
                    self._log.log("AGENT", f"unknown: {reason}")
                return reply
            result = self._execute(tool_call)
            self._log.log("TOOL", result.message)
            messages.append(ChatMessage("user", self._build_tool_feedback(tool_call.tool_name, result)).to_dict())
            self._log.log("AGENT", f"step {step}: {tool_call.tool_name}")
        self._log.log("AGENT", "max steps reached")
        return reply

    def _build_command_history(self, command: str) -> list[dict[str, str]]:
        prior = [item.to_dict() for item in self._history.get_messages()]
        return [*prior, ChatMessage("user", f"Command: {command}").to_dict()]

    def _remember_exchange(self, command: str, reply: str) -> None:
        self._history.append(ChatMessage("user", f"Command: {command}"))
        if reply:
            self._history.append(ChatMessage("assistant", reply))

    def _execute(self, tool_call: ToolCall) -> ToolResult:
        try:
            return self._registry.get(tool_call.tool_name).execute(tool_call.parameters)
        except KeyError:
            return ToolResult(False, f"unknown tool: {tool_call.tool_name}")

    def _parse_tool_call(self, raw: str) -> ToolCall:
        try:
            data = json.loads(raw.strip())
            return ToolCall(tool_name=data.pop("tool"), parameters=data)
        except Exception as exc:
            self._log.log("AGENT", f"invalid JSON from model: {exc}")
            return ToolCall(
                "unknown",
                {
                    "reply": "I could not interpret the model response.",
                    "reason": "model did not return valid tool JSON",
                },
            )

    def _build_system_prompt(self) -> str:
        return "\n".join([_SYSTEM_PROMPT, self._registry.build_schema_text()])

    def _build_context_message(self, ctx: DesktopContext) -> str:
        windows = "\n".join(
            f"  {item.title[:80]} [{item.width}x{item.height} at {item.x},{item.y}]"
            for item in ctx.open_windows[:_MAX_WINDOWS]
        )
        apps = "\n".join(
            f"  {item.name[:_MAX_APP_NAME_LENGTH]}"
            for item in ctx.available_applications[:_MAX_APPS]
        )
        more_windows = max(0, len(ctx.open_windows) - _MAX_WINDOWS)
        more_apps = max(0, len(ctx.available_applications) - _MAX_APPS)
        window_tail = f"\n  ... and {more_windows} more" if more_windows else ""
        app_tail = f"\n  ... and {more_apps} more" if more_apps else ""
        return "\n".join([
            "Desktop context:",
            f"Active window: {ctx.active_window_title}",
            f"Open windows:\n{windows or '  none'}{window_tail}",
            f"Available apps:\n{apps or '  none'}{app_tail}",
        ])

    def _build_tool_feedback(self, tool_name: str, result: ToolResult) -> str:
        status = "success" if result.success else "failure"
        return f"Tool {tool_name} returned {status}: {result.message}"
