from tusk.kernel.interfaces.conversation_logger import ConversationLogger
from tusk.kernel.interfaces.llm_provider import LLMProvider
from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.schemas.chat_message import ChatMessage
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_call_parser import ToolCallParser

__all__ = ["AgentToolLoop"]

_MAX_STEPS = 10
_TERMINAL_TOOLS = frozenset({"done", "unknown", "clarify"})


class AgentToolLoop:
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: object,
        log_printer: LogPrinter,
        conversation_logger: ConversationLogger | None,
        parser: ToolCallParser,
        failure_builder: object,
    ) -> None:
        self._llm = llm_provider
        self._registry = tool_registry
        self._log = log_printer
        self._logger = conversation_logger
        self._parser = parser
        self._failure_builder = failure_builder
        self._last_failure_reply = ""

    def run(self, prompt: str, context_message: str, command_history: list[dict[str, str]]) -> str:
        reply = ""
        messages = self._messages(context_message, command_history)
        for step in range(1, _MAX_STEPS + 1):
            outcome = self._step(prompt, messages, reply)
            reply = outcome["reply"]
            if outcome["stop"]:
                return reply
            self._continue(messages, outcome, step)
        self._log.log("AGENT", "max steps reached")
        return reply

    def _step(self, prompt: str, messages: list[dict[str, str]], reply: str) -> dict:
        raw = self._raw_response(prompt, messages)
        if raw is None:
            return self._failure_outcome(reply)
        tool_call = self._parser.parse(raw)
        reply = tool_call.parameters.pop("reply", reply)
        self._speak(reply)
        if tool_call.tool_name in _TERMINAL_TOOLS:
            return self._terminal_outcome(tool_call, reply)
        return self._tool_outcome(tool_call, reply)

    def _messages(self, context_message: str, command_history: list[dict[str, str]]) -> list[dict[str, str]]:
        return [ChatMessage("user", context_message).to_dict(), *command_history]

    def _continue(self, messages: list[dict[str, str]], outcome: dict, step: int) -> None:
        self._add_feedback(messages, outcome["tool"], outcome["result"])
        self._log.log("AGENT", f"step {step}: {outcome['tool']}")

    def _raw_response(self, prompt: str, messages: list[dict[str, str]]) -> str | None:
        try:
            raw = self._llm.complete_messages(prompt, messages)
        except Exception as exc:
            self._log.log("AGENT", f"llm failure: {exc}")
            return self._failure_stop(exc)
        self._remember_raw(messages, raw)
        return raw

    def _failure_stop(self, exc: Exception) -> None:
        self._last_failure_reply = self._failure_builder.build(exc)
        self._speak(self._last_failure_reply)
        return None

    def _speak(self, reply: str) -> None:
        if reply:
            self._log.log("TUSK", reply)

    def _log_unknown(self, tool_call: object) -> None:
        if tool_call.tool_name == "unknown":
            self._log.log("AGENT", f"unknown: {tool_call.parameters.get('reason', 'unknown reason')}")

    def _terminal_outcome(self, tool_call: object, reply: str) -> dict:
        self._log_unknown(tool_call)
        return {"reply": reply, "stop": True, "tool": tool_call.tool_name, "result": ToolResult(True, reply)}

    def _tool_outcome(self, tool_call: object, reply: str) -> dict:
        result = self._execute(tool_call)
        return {"reply": reply, "stop": False, "tool": tool_call.tool_name, "result": result}

    def _failure_outcome(self, reply: str) -> dict:
        failure_reply = self._last_failure_reply or reply
        return {"reply": failure_reply, "stop": True, "tool": "unknown", "result": ToolResult(False, failure_reply)}

    def _execute(self, tool_call: object) -> ToolResult:
        try:
            return self._registry.get(tool_call.tool_name).execute(tool_call.parameters)
        except KeyError:
            return ToolResult(False, f"unknown tool: {tool_call.tool_name}")

    def _add_feedback(self, messages: list[dict[str, str]], name: str, result: ToolResult) -> None:
        self._log.log("TOOL", result.message)
        feedback = ChatMessage("user", self._feedback_text(name, result))
        self._record(feedback)
        messages.append(feedback.to_dict())

    def _feedback_text(self, tool_name: str, result: ToolResult) -> str:
        status = "success" if result.success else "failure"
        return f"Tool {tool_name} returned {status}: {result.message}"

    def _record(self, message: ChatMessage) -> None:
        if self._logger:
            self._logger.log_message(message)

    def _remember_raw(self, messages: list[dict[str, str]], raw: str) -> None:
        self._log.log("LLM", f"[{self._llm.label}] agent → {raw!r}")
        message = ChatMessage("assistant", raw)
        self._record(message)
        messages.append(message.to_dict())
