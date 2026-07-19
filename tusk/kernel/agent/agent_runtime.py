from collections.abc import Callable

from tusk.kernel.agent.runtime.model_failure_reply_builder import ModelFailureReplyBuilder
from tusk.kernel.tools.repeated_tool_call_guard import RepeatedToolCallGuard
from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.kernel.agent.agent_profile import AgentProfile
from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.agent_run_request import AgentRunRequest
from tusk.kernel.agent.session.store import Store
from tusk.kernel.agent.runtime.message_history_builder import MessageHistoryBuilder
from tusk.kernel.agent.runtime.result_factory import ResultFactory
from tusk.kernel.agent.runtime.step_recorder import StepRecorder
from tusk.kernel.agent.runtime.turn_guards import TurnGuards
from tusk.shared.logging.interfaces.log_printer import LogPrinter


class AgentRuntime:
    def __init__(
        self, session_store: Store, log_printer: LogPrinter,
        step_recorder: StepRecorder, interrupt_token: object | None = None,
    ) -> None:
        self._store = session_store
        self._log = log_printer
        self._token = interrupt_token
        self._failure = ModelFailureReplyBuilder()
        self._history = MessageHistoryBuilder(session_store)
        self._results = ResultFactory(session_store)
        self._record = step_recorder

    def run(
        self, request: AgentRunRequest, profile: AgentProfile,
        tools: list[dict[str, object]], executor: Callable[[ToolCall, str], ToolResult],
    ) -> AgentResult:
        session_id = self._session_id(request, profile)
        messages = self._history.build(session_id, request)
        self._record.append_message(session_id, "user", request.instruction)
        messages.append({"role": "user", "content": request.instruction})
        return self._loop(session_id, profile, tools, messages, executor)

    def _session_id(self, request: AgentRunRequest, profile: AgentProfile) -> str:
        session_id = request.session_id or self._store.create_session_id()
        if not self._store.has_session(session_id):
            self._start(session_id, profile, request)
        return session_id

    def _start(self, session_id: str, profile: AgentProfile, request: AgentRunRequest) -> None:
        self._store.start_session(session_id, profile.profile_id, request.parent_session_id, request.parent_call_id, request.metadata)

    def _loop(
        self, session_id: str, profile: AgentProfile, tools: list[dict[str, object]],
        messages: list[dict[str, str]], executor: Callable[[ToolCall, str], ToolResult],
    ) -> AgentResult:
        repeat = RepeatedToolCallGuard()
        guards = TurnGuards()
        for step in range(1, profile.max_steps + 1):
            if self._interrupted():
                return self._cancelled(session_id)
            result = self._step(session_id, profile, tools, messages, executor, repeat, guards, step)
            if result is not None:
                return result
        return self._failed(session_id, "max steps reached")

    def _interrupted(self) -> bool:
        return self._token is not None and self._token.is_interrupted

    def _cancelled(self, session_id: str) -> AgentResult:
        result = self._results.cancelled(session_id)
        return self._results.persist(session_id, result, result.reply_text())

    def _step(
        self, session_id: str, profile: AgentProfile, tools: list[dict[str, object]],
        messages: list[dict[str, str]], executor: Callable[[ToolCall, str], ToolResult],
        repeat: RepeatedToolCallGuard, guards: TurnGuards, step: int,
    ) -> AgentResult | None:
        tool_call = self._tool_call(profile, messages, tools)
        self._record.requested(session_id, step, tool_call)
        finished = self._guard_result(session_id, profile.profile_id, tool_call, repeat, guards)
        if finished is not None:
            return finished
        result = executor(tool_call, session_id)
        self._record.result(session_id, step, tool_call, result)
        self._record.appended(messages, tool_call, result)
        guards.observe(tool_call, result)
        return None

    def _guard_result(
        self, session_id: str, profile_id: str, tool_call: ToolCall,
        repeat: RepeatedToolCallGuard, guards: TurnGuards,
    ) -> AgentResult | None:
        if tool_call.tool_name == "done":
            return self._finish(session_id, tool_call.parameters)
        violation = guards.violation(profile_id, tool_call)
        if violation:
            return self._failed(session_id, violation)
        if repeat.repeated(tool_call):
            return self._failed(session_id, "repeated identical tool call")
        return None

    def _tool_call(self, profile: AgentProfile, messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ToolCall:
        try:
            return profile.llm_provider.complete_tool_call(profile.system_prompt, messages, tools)
        except Exception as exc:
            self._log.log("AGENT", f"llm failure: {exc}")
            text = self._failure.build(exc)
            return ToolCall("done", {"status": "failed", "summary": text, "text": text})

    def _finish(self, session_id: str, parameters: dict[str, object]) -> AgentResult:
        result = self._results.from_parameters(session_id, parameters)
        return self._results.persist(session_id, result, result.reply_text())

    def _failed(self, session_id: str, reason: str) -> AgentResult:
        result = self._results.failed(session_id, reason)
        return self._results.persist(session_id, result, result.reply_text())
