import types

from tusk.kernel.agent import MainAgent
from tusk.kernel.execution_agent import ExecutionAgent
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry

__all__ = ["HistoryRecorder", "make_agent", "make_executor", "make_registry_tool"]


class HistoryRecorder:
    def __init__(self) -> None:
        self.stored: list[tuple[str, str]] = []

    def append(self, message) -> None:
        self.stored.append((message.role, message.content))

    def get_messages(self) -> list[object]:
        return []


def make_agent(
    llm: object,
    history: object | None = None,
    registry: ToolRegistry | None = None,
    log: object | None = None,
) -> MainAgent:
    history = history or types.SimpleNamespace(append=lambda message: None, get_messages=lambda: [])
    log = log or types.SimpleNamespace(log=lambda *args: None)
    registry = registry or ToolRegistry()
    return MainAgent(llm, registry, history, log)


def make_executor(llm: object, registry: ToolRegistry | None = None, log: object | None = None) -> ExecutionAgent:
    log = log or types.SimpleNamespace(log=lambda *args: None)
    registry = registry or ToolRegistry()
    return ExecutionAgent(llm, registry, log)


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
