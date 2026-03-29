import json

from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry
from tusk.lib.agent.agent_child_runner import AgentChildRunner
from tusk.lib.agent.agent_profile import AgentProfile
from tusk.lib.agent.agent_result import AgentResult
from tusk.lib.agent.agent_run_guard import AgentRunGuard
from tusk.lib.agent.agent_run_request import AgentRunRequest
from tusk.lib.agent.agent_runtime import AgentRuntime
from tusk.lib.agent.executor_tool_guard import ExecutorToolGuard
from tusk.lib.agent.planner_request_enricher import PlannerRequestEnricher
from tusk.lib.agent.planner_result_validator import PlannerResultValidator
from tusk.lib.agent.planner_runtime_tool_resolver import PlannerRuntimeToolResolver
from tusk.lib.agent.agent_session_store import AgentSessionStore
from tusk.lib.agent.agent_toolset_builder import AgentToolsetBuilder
from tusk.lib.logging.interfaces.log_printer import LogPrinter

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
        self._store = session_store
        self._log = log_printer
        self._runtime = AgentRuntime(session_store, log_printer)
        self._guard = AgentRunGuard()
        self._children = AgentChildRunner(session_store)
        self._executor_tools = ExecutorToolGuard()
        self._planner_request = PlannerRequestEnricher()
        self._planner_results = PlannerResultValidator()
        self._resolved_tools = PlannerRuntimeToolResolver(session_store)
        self._tools = AgentToolsetBuilder(tool_registry)

    def run(self, request: AgentRunRequest) -> AgentResult:
        return self._run(request, ())

    def _run(self, request: AgentRunRequest, lineage: tuple[tuple[str, str, str], ...]) -> AgentResult:
        request = self._prepared(request)
        profile = self._profiles.get(request.profile_id)
        failure = self._guard.validate(request, profile, lineage)
        if failure:
            return failure
        assert profile is not None
        failure = self._executor_tools.validate(profile.profile_id, request, self._tools.runtime_names(profile, request))
        if failure:
            return failure
        tools = self._tools.build(profile, request)
        run = lambda call, session_id: self._execute(call, request, lineage, session_id)
        return self._runtime.run(request, profile, tools, run)

    def _prepared(self, request: AgentRunRequest) -> AgentRunRequest:
        request = self._planner_request.enrich(request, self._registry.planner_tool_names())
        return self._resolved_tools.resolve(request, self._registry.real_tool_names())

    def _execute(
        self,
        tool_call: ToolCall,
        request: AgentRunRequest,
        lineage: tuple[tuple[str, str, str], ...],
        session_id: str,
    ) -> ToolResult:
        if tool_call.tool_name == "run_agent":
            return self._run_agent(tool_call, request, lineage, session_id)
        if tool_call.tool_name == "list_available_tools":
            return self._list_available_tools()
        try:
            return self._registry.get(tool_call.tool_name).execute(tool_call.parameters)
        except KeyError:
            return ToolResult(False, f"unknown tool: {tool_call.tool_name}")

    def _run_agent(
        self,
        tool_call: ToolCall,
        request: AgentRunRequest,
        lineage: tuple[tuple[str, str, str], ...],
        session_id: str,
    ) -> ToolResult:
        child = self._children.request(tool_call, session_id)
        if not child.instruction:
            return self._children.invalid_request()
        self._children.started(session_id, child)
        child_lineage = self._guard.child_lineage(request, session_id, lineage)
        result = self._run(child, child_lineage)
        result = self._planner_results.validate(child.profile_id, result, self._registry.real_tool_names())
        self._children.finished(session_id, result)
        return self._children.result(result)

    def _list_available_tools(self) -> ToolResult:
        tools = [
            {"name": tool.name, "description": tool.description, "input_schema": tool.input_schema, "source": tool.source}
            for tool in self._registry.planner_tools()
        ]
        return ToolResult(True, json.dumps({"tools": tools}), {"tools": tools})
