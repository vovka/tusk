from types import SimpleNamespace

from tusk.kernel.tool_registry import ToolRegistry
from tusk.kernel.visible_tool_definition_builder import VisibleToolDefinitionBuilder
from tusk.lib.agent.agent_profile import AgentProfile
from tusk.lib.agent.agent_run_request import AgentRunRequest

__all__ = ["AgentToolsetBuilder"]


class AgentToolsetBuilder:
    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._registry = tool_registry
        self._definitions = VisibleToolDefinitionBuilder()

    def build(self, profile: AgentProfile, request: AgentRunRequest) -> list[dict[str, object]]:
        builtins = [self._done_tool(profile)]
        names = set(profile.static_tool_names)
        names.update(self.runtime_names(profile, request))
        return [*builtins, *self._builtin_tools(names), *self._registry.definitions_for(names)]

    def runtime_names(self, profile: AgentProfile, request: AgentRunRequest) -> set[str]:
        return self._runtime_names(profile, request)

    def _builtin_tools(self, names: set[str]) -> list[dict[str, object]]:
        builtins: list[dict[str, object]] = []
        for name in ("run_agent", "list_available_tools"):
            if name in names:
                builtins.append(self._tool(name))
                names.remove(name)
        return builtins

    def _runtime_names(self, profile: AgentProfile, request: AgentRunRequest) -> set[str]:
        requested = set(request.runtime_tool_names)
        allowed = set(profile.runtime_allowed_tool_names)
        if "*" in allowed:
            return requested.intersection(self._registry.real_tool_names())
        return allowed.intersection(requested).intersection(self._registry.real_tool_names())

    def _done_tool(self, profile: AgentProfile) -> dict[str, object]:
        return self._tool("done", _done_schema(profile.profile_id))

    def _tool(self, name: str, schema: dict[str, object] | None = None) -> dict[str, object]:
        schemas = {
            "done": schema or _done_schema("default"),
            "run_agent": _run_agent_schema(),
            "list_available_tools": {"type": "object", "properties": {}},
        }
        tool = SimpleNamespace(name=name, description=_description(name), input_schema=schemas[name])
        return self._definitions.build([tool])[0]


def _description(name: str) -> str:
    descriptions = {
        "done": "Finish the agent run with a structured result.",
        "run_agent": "Run a predefined sub-agent profile and wait for its final result.",
        "list_available_tools": "Return the available runtime-exposable tool catalog.",
    }
    return descriptions[name]


def _done_schema(profile_id: str) -> dict[str, object]:
    if profile_id == "planner":
        return _planner_done_schema()
    return _default_done_schema()


def _default_done_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["done", "clarify", "unknown", "failed", "need_tools"]},
            "summary": {"type": "string"},
            "text": {"type": "string"},
            "payload": {"type": "object"},
            "artifact_refs": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["status", "summary"],
    }


def _planner_done_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["done", "clarify", "unknown", "failed"]},
            "summary": {"type": "string"},
            "text": {"type": "string"},
            "payload": {
                "type": "object",
                "properties": {
                    "selected_tool_names": {"type": "array", "items": {"type": "string"}},
                    "plan_text": {"type": "string"},
                },
                "required": ["selected_tool_names"],
            },
            "artifact_refs": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["status", "summary", "payload"],
    }


def _run_agent_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "profile_id": {"type": "string", "enum": ["planner", "executor", "default"]},
            "instruction": {"type": "string"},
            "runtime_tool_names": {"type": "array", "items": {"type": "string"}},
            "session_refs": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["instruction"],
    }
