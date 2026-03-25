from tusk.kernel.described_tool_tracker import DescribedToolTracker
from tusk.kernel.interfaces.conversation_logger import ConversationLogger
from tusk.kernel.interfaces.llm_provider import LLMProvider
from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.repeated_tool_call_guard import RepeatedToolCallGuard
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_call_executor import ToolCallExecutor
from tusk.kernel.tool_loop_recorder import ToolLoopRecorder

__all__ = ["AgentToolLoop"]

_MAX_STEPS = 16
_TERMINAL_TOOLS = frozenset({"done", "unknown", "clarify"})


class AgentToolLoop:
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: object,
        log_printer: LogPrinter,
        usage_recorder: object,
        conversation_logger: ConversationLogger | None,
        failure_builder: object,
    ) -> None:
        self._llm = llm_provider
        self._log = log_printer
        self._registry = tool_registry
        self._failure_builder = failure_builder
        self._recorder = ToolLoopRecorder(log_printer, conversation_logger)
        self._described = DescribedToolTracker()
        self._repeat_guard = RepeatedToolCallGuard()
        self._last_failure_reply = ""
        self._executor = ToolCallExecutor(tool_registry, usage_recorder)

    def run(self, prompt: str, history: list[dict[str, str]], tools: list[dict[str, object]]) -> str:
        reply = ""
        messages = list(history)
        for step in range(1, _MAX_STEPS + 1):
            outcome = self._step(prompt, messages, self._tools(tools), reply)
            reply = outcome["reply"]
            if outcome["stop"]:
                return reply
            self._continue(messages, outcome, step)
        self._log.log("AGENT", "max steps reached")
        return reply

    def _step(self, prompt: str, messages: list[dict[str, str]], tools: list[dict[str, object]], reply: str) -> dict:
        tool_call = self._tool_call(prompt, messages, tools)
        if tool_call is None:
            return self._failure_outcome(reply)
        next_reply = str(tool_call.parameters.get("reply", reply))
        if tool_call.tool_name in _TERMINAL_TOOLS:
            return self._terminal_outcome(tool_call, next_reply)
        if self._repeat_guard.repeated(tool_call):
            return self._repeat_outcome()
        return self._tool_outcome(tool_call, next_reply)

    def _tool_call(
        self,
        prompt: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]],
    ) -> ToolCall | None:
        try:
            tool_call = self._llm.complete_tool_call(prompt, messages, tools)
        except Exception as exc:
            self._log.log("AGENT", f"llm failure: {exc}")
            return self._failure_stop(exc)
        self._recorder.remember_tool_call(messages, tool_call, self._llm.label)
        return tool_call

    def _continue(self, messages: list[dict[str, str]], outcome: dict, step: int) -> None:
        self._described.remember(outcome["call"], outcome["result"])
        self._recorder.add_feedback(messages, outcome["tool"], outcome["result"])
        self._log.log("AGENT", f"step {step}: {outcome['tool']}")

    def _failure_stop(self, exc: Exception) -> None:
        self._last_failure_reply = self._failure_builder.build(exc)
        self._speak(self._last_failure_reply)
        return None

    def _speak(self, reply: str) -> None:
        if reply:
            self._log.log("TUSK", reply)

    def _terminal_outcome(self, tool_call: ToolCall, reply: str) -> dict:
        self._log_unknown(tool_call)
        return {"reply": reply, "stop": True, "tool": tool_call.tool_name, "result": ToolResult(True, reply)}

    def _log_unknown(self, tool_call: ToolCall) -> None:
        if tool_call.tool_name == "unknown":
            reason = tool_call.parameters.get("reason", "unknown reason")
            self._log.log("AGENT", f"unknown: {reason}")

    def _tool_outcome(self, tool_call: ToolCall, reply: str) -> dict:
        result = self._executor.execute(tool_call, self._described.names())
        if result.success:
            self._speak(reply)
        return {"reply": reply, "stop": False, "tool": tool_call.tool_name, "result": result, "call": tool_call}

    def _failure_outcome(self, reply: str) -> dict:
        text = self._last_failure_reply or reply
        return {"reply": text, "stop": True, "tool": "unknown", "result": ToolResult(False, text), "call": ToolCall("unknown", {})}

    def _repeat_outcome(self) -> dict:
        text = "I need a different action or clarification to continue."
        self._log.log("AGENT", "repeated identical tool call")
        self._speak(text)
        return {"reply": text, "stop": True, "tool": "unknown", "result": ToolResult(False, text), "call": ToolCall("unknown", {})}

    def _tools(self, base: list[dict[str, object]]) -> list[dict[str, object]]:
        return [*base, *self._registry.visible_tool_definitions(self._described.names())]
