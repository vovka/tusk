from tusk.shared.schemas.tool_call import ToolCall
from tusk.shared.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry
from tusk.kernel.agent.agent_child_runner import AgentChildRunner
from tusk.kernel.agent.agent_profile import AgentProfile
from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.agent_run_guard import AgentRunGuard
from tusk.kernel.agent.agent_run_request import AgentRunRequest
from tusk.kernel.agent.agent_runtime import AgentRuntime
from tusk.kernel.agent.agent_session_store import AgentSessionStore
from tusk.kernel.agent.agent_tool_catalog import AgentToolCatalog
from tusk.kernel.agent.agent_toolset_builder import AgentToolsetBuilder
from tusk.kernel.agent.executor_tool_guard import ExecutorToolGuard
from tusk.kernel.agent.orchestrator_tool_dispatcher import OrchestratorToolDispatcher
from tusk.kernel.agent.planner_request_enricher import PlannerRequestEnricher
from tusk.kernel.agent.planner_result_validator import PlannerResultValidator
from tusk.kernel.agent.planner_runtime_tool_resolver import PlannerRuntimeToolResolver
from tusk.kernel.agent.tool_sequence_executor import ToolSequenceExecutor
from tusk.shared.logging.interfaces.log_printer import LogPrinter

__all__ = ["AgentOrchestrator"]


class AgentOrchestrator:
    def __init__(
        self,
        profiles: dict[str, AgentProfile],
        tool_registry: ToolRegistry,
        session_store: AgentSessionStore,
        log_printer: LogPrinter,
    ) -> None:
        self._profiles = profiles
        self._registry = tool_registry
        self._log = log_printer
        self._init_components(session_store, log_printer, tool_registry)

    def _init_components(self, store: AgentSessionStore, log: LogPrinter, registry: ToolRegistry) -> None:
        self._runtime = AgentRuntime(store, log)
        self._guard = AgentRunGuard()
        self._children = AgentChildRunner(store)
        self._executor_tools = ExecutorToolGuard()
        self._planner_request = PlannerRequestEnricher()
        self._catalog = AgentToolCatalog(registry)
        self._planner_results = PlannerResultValidator(log)
        self._resolved_tools = PlannerRuntimeToolResolver(store)
        self._tools = AgentToolsetBuilder(registry)
        self._dispatcher = OrchestratorToolDispatcher(registry, self._catalog, ToolSequenceExecutor(registry, store))

    def run(self, request: AgentRunRequest) -> AgentResult:
        return self._run(request, ())

    def _run(self, request: AgentRunRequest, lineage: tuple[tuple[str, str, str], ...]) -> AgentResult:
        request = self._prepared(request)
        profile = self._profiles.get(request.profile_id)
        failure = self._validate(request, profile, lineage)
        if failure:
            return failure
        assert profile is not None
        tools = self._tools.build(profile, request)
        run = lambda call, sid: self._execute(call, request, lineage, sid)
        return self._runtime.run(request, profile, tools, run)

    def _validate(self, request: AgentRunRequest, profile: AgentProfile | None, lineage: tuple[tuple[str, str, str], ...]) -> AgentResult | None:
        failure = self._guard.validate(request, profile, lineage)
        if failure:
            return failure
        if profile is not None:
            return self._check_executor(profile, request)
        return None

    def _prepared(self, request: AgentRunRequest) -> AgentRunRequest:
        request = self._planner_request.enrich(request, self._catalog.prompt_text())
        return self._resolved_tools.resolve(request, self._registry.real_tool_names())

    def _check_executor(self, profile: AgentProfile, request: AgentRunRequest) -> AgentResult | None:
        names = self._tools.runtime_names(profile, request)
        return self._executor_tools.validate(profile.profile_id, request, names)

    def _execute(self, call: ToolCall, request: AgentRunRequest, lineage: tuple[tuple[str, str, str], ...], sid: str) -> ToolResult:
        agent_runner = lambda tc: self._run_agent(tc, request, lineage, sid)
        return self._dispatcher.dispatch(call, agent_runner, sid, set(request.runtime_tool_names), request.sequence_plan)

    def _run_agent(self, tool_call: ToolCall, request: AgentRunRequest, lineage: tuple[tuple[str, str, str], ...], session_id: str) -> ToolResult:
        child = self._children.request(tool_call, session_id)
        if not child.instruction:
            return self._children.invalid_request()
        return self._delegate(child, request, lineage, session_id)

    def _delegate(self, child: AgentRunRequest, request: AgentRunRequest, lineage: tuple[tuple[str, str, str], ...], session_id: str) -> ToolResult:
        self._children.started(session_id, child)
        child_lineage = self._guard.child_lineage(request, session_id, lineage)
        result = self._run(child, child_lineage)
        result = self._planner_results.validate(child.profile_id, result, self._registry)
        self._children.finished(session_id, child.profile_id, result)
        return self._children.result(child.profile_id, result)
