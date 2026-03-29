import tempfile
import types

from tusk.kernel.agent import MainAgent
from tusk.kernel.agent_profiles import build_agent_profiles
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry
from tusk.lib.agent import AgentOrchestrator, FileAgentSessionStore

__all__ = ["HistoryRecorder", "make_agent", "make_registry_tool"]


class HistoryRecorder:
    def __init__(self) -> None:
        self.stored: list[tuple[str, str]] = []

    def append(self, message: object) -> None:
        self.stored.append((message.role, message.content))

    def get_messages(self) -> list[object]:
        return []


def make_agent(
    llm: object,
    history: object | None = None,
    registry: ToolRegistry | None = None,
    log: object | None = None,
    planner_llm: object | None = None,
    executor_llm: object | None = None,
    default_llm: object | None = None,
) -> MainAgent:
    history = history or types.SimpleNamespace(append=lambda message: None, get_messages=lambda: [])
    log = log or types.SimpleNamespace(log=lambda *args: None)
    registry = registry or ToolRegistry()
    store = FileAgentSessionStore(tempfile.mkdtemp(prefix="tusk-agent-tests-"))
    llms = _llm_map(llm, planner_llm, executor_llm, default_llm)
    profiles = build_agent_profiles(types.SimpleNamespace(get=lambda name: llms[name]))
    return MainAgent(AgentOrchestrator(profiles, registry, store, log), history)


def _llm_map(llm: object, planner: object | None, executor: object | None, default: object | None) -> dict[str, object]:
    return {
        "conversation_agent": llm,
        "planner_agent": planner or llm,
        "executor_agent": executor or llm,
        "default_agent": default or llm,
    }


def make_registry_tool(
    name: str,
    message: str,
    *,
    planner_visible: bool = True,
    input_schema: dict | None = None,
) -> object:
    return types.SimpleNamespace(
        name=name,
        description=message,
        input_schema=input_schema or {"type": "object", "properties": {"text": {"type": "string"}}},
        execute=lambda _: ToolResult(True, message),
        source="gnome",
        planner_visible=planner_visible,
    )
