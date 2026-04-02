import tempfile

from tests.kernel_api_support import make_registry_tool
from tusk.kernel.agent.file_agent_session_store import FileAgentSessionStore
from tusk.kernel.agent.tool_sequence_executor import ToolSequenceExecutor
from tusk.kernel.tool_registry import ToolRegistry
from tusk.shared.schemas.tool_result import ToolResult


def test_sequence_executor_runs_steps_in_order() -> None:
    seen: list[dict[str, object]] = []
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed", sequence_callable=True, execute=_record(seen)))
    result = _executor(registry).execute("s1", _plan("hello"), {"gnome.type_text"})
    assert result.success is True
    assert seen == [{"text": "hello"}]
    assert result.data["completed_step_ids"] == ["s1"]


def test_sequence_executor_aborts_on_failed_step() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed", sequence_callable=True, execute=_fail))
    result = _executor(registry).execute("s1", _plan("hello"), {"gnome.type_text"})
    assert result.success is False
    assert result.data["failed_step_id"] == "s1"


def _executor(registry: ToolRegistry) -> ToolSequenceExecutor:
    store = FileAgentSessionStore(tempfile.mkdtemp(prefix="tusk-sequence-exec-"))
    return ToolSequenceExecutor(registry, store)


def _plan(text: str) -> dict[str, object]:
    step = {"id": "s1", "tool_name": "gnome.type_text", "args": {"text": text}}
    return {"goal": "Type text", "steps": [step]}


def _record(seen: list[dict[str, object]]) -> object:
    return lambda arguments: _append(seen, arguments)


def _append(seen: list[dict[str, object]], arguments: dict[str, object]) -> ToolResult:
    seen.append(dict(arguments))
    return ToolResult(True, "typed", {"echo": dict(arguments)})


def _fail(arguments: dict[str, object]) -> ToolResult:
    return ToolResult(False, f"failed: {arguments['text']}")
