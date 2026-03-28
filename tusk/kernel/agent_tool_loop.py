from tusk.lib.llm.interfaces.llm_provider import LLMProvider
from tusk.lib.logging.interfaces.log_printer import LogPrinter
from tusk.kernel.model_failure_reply_builder import ModelFailureReplyBuilder
from tusk.kernel.repeated_tool_call_guard import RepeatedToolCallGuard
from tusk.kernel.schemas.task_execution_result import TaskExecutionResult
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_call_executor import ToolCallExecutor
from tusk.kernel.tool_loop_recorder import ToolLoopRecorder

__all__ = ["AgentToolLoop"]

_MAX_STEPS = 16


class AgentToolLoop:
    def __init__(self, llm_provider: LLMProvider, tool_registry: object, log_printer: LogPrinter) -> None:
        self._llm = llm_provider
        self._log = log_printer
        self._recorder = ToolLoopRecorder(log_printer)
        self._repeat_guard = RepeatedToolCallGuard()
        self._executor = ToolCallExecutor(tool_registry)
        self._failure = ModelFailureReplyBuilder()

    def run(
        self,
        prompt: str,
        history: list[dict[str, str]],
        tools: list[dict[str, object]],
        allowed: set[str],
        terminals: set[str],
    ) -> TaskExecutionResult:
        messages = list(history)
        for step in range(1, _MAX_STEPS + 1):
            result = self._step(prompt, messages, tools, allowed, terminals)
            if result.status:
                return result
            self._log.log("AGENT", f"step {step}: {result.reason}")
        return self._stopped("max steps reached", "I couldn't finish the task.")

    def _step(
        self,
        prompt: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]],
        allowed: set[str],
        terminals: set[str],
    ) -> TaskExecutionResult:
        tool_call = self._tool_call(prompt, messages, tools)
        if tool_call.tool_name in terminals:
            return self._terminal(tool_call)
        if self._repeat_guard.repeated(tool_call):
            return self._stopped("repeated identical tool call", "I need a different action or clarification to continue.")
        result = self._executor.execute(tool_call, allowed)
        self._recorder.add_feedback(messages, tool_call.tool_name, result)
        return TaskExecutionResult("", "", tool_call.tool_name) if result else TaskExecutionResult("failed", "", "")

    def _tool_call(self, prompt: str, messages: list[dict[str, str]], tools: list[dict[str, object]]) -> ToolCall:
        try:
            tool_call = self._llm.complete_tool_call(prompt, messages, tools)
        except Exception as exc:
            self._log.log("AGENT", f"llm failure: {exc}")
            return ToolCall("unknown", {"reply": self._failure.build(exc), "reason": str(exc)})
        self._recorder.remember_tool_call(messages, tool_call, self._llm.label)
        return tool_call

    def _terminal(self, tool_call: ToolCall) -> TaskExecutionResult:
        if tool_call.tool_name == "unknown":
            self._log.log("AGENT", f"unknown: {tool_call.parameters.get('reason', 'unknown reason')}")
        if tool_call.tool_name == "need_tools":
            return TaskExecutionResult("need_tools", "", str(tool_call.parameters.get("reason", "")), str(tool_call.parameters.get("needed_capability", "")))
        return TaskExecutionResult(tool_call.tool_name, str(tool_call.parameters.get("reply", "")), str(tool_call.parameters.get("reason", "")))

    def _stopped(self, reason: str, reply: str) -> TaskExecutionResult:
        self._log.log("AGENT", reason)
        self._log.log("TUSK", reply)
        return TaskExecutionResult("failed", reply, reason)
