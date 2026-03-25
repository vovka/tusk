import types

from tusk.kernel.agent import MainAgent
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry
from tusk.kernel.tool_usage_recorder import ToolUsageRecorder
from tusk.kernel.tool_usage_store import ToolUsageStore

__all__ = ["HistoryRecorder", "make_agent", "make_registry_tool"]


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
    usage = ToolUsageRecorder(registry, ToolUsageStore("/tmp/tusk-test-usage.json", lambda: 1.0))
    return MainAgent(llm, registry, history, log, usage)


def make_registry_tool(
    name: str,
    message: str,
    *,
    broker: bool = False,
    prompt_visible: bool = False,
) -> object:
    return types.SimpleNamespace(
        name=name,
        description=message,
        input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
        execute=lambda _: ToolResult(True, message),
        source="gnome",
        broker=broker,
        prompt_visible=prompt_visible,
    )
