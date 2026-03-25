import types

from tusk.kernel.agent import MainAgent
from tusk.kernel.schemas.desktop_context import DesktopContext
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry

__all__ = ["HistoryRecorder", "make_agent", "make_context", "make_registry_tool"]


class HistoryRecorder:
    def __init__(self) -> None:
        self.stored: list[tuple[str, str]] = []

    def append(self, message) -> None:
        self.stored.append((message.role, message.content))

    def get_messages(self) -> list[object]:
        return []


def make_agent(llm: object, history: object | None = None, context: object | None = None, log: object | None = None) -> MainAgent:
    history = history or types.SimpleNamespace(append=lambda message: None, get_messages=lambda: [])
    context = context or types.SimpleNamespace(get_context=lambda: DesktopContext("", ""))
    log = log or types.SimpleNamespace(log=lambda *args: None)
    return MainAgent(llm, ToolRegistry(), history, context, log)


def make_context(title: str = "", app_count: int = 0) -> DesktopContext:
    apps = [types.SimpleNamespace(name=f"app-{index}") for index in range(app_count)]
    return DesktopContext(title, "", available_applications=apps)


def make_registry_tool(name: str, message: str) -> object:
    return types.SimpleNamespace(
        name=name,
        description="tool",
        input_schema={"type": "object"},
        execute=lambda _: ToolResult(True, message),
        source="gnome",
    )
