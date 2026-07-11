import tempfile

from tests.kernel_api_support import make_registry_tool
from tusk.kernel.agent.session.file_store import FileStore
from tusk.kernel.agent.tool_sequence.executor import Executor
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_result import ToolResult


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


def _executor(registry: ToolRegistry) -> Executor:
    store = FileStore(tempfile.mkdtemp(prefix="tusk-sequence-exec-"))
    return Executor(registry, store)


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


def test_sequence_executor_cancels_between_steps() -> None:
    from tusk.shared.interrupt import InterruptToken
    token = InterruptToken()
    seen: list[dict[str, object]] = []
    registry = ToolRegistry()
    execute = _record_then_interrupt(seen, token)
    registry.register(make_registry_tool("gnome.type_text", "typed", sequence_callable=True, execute=execute))
    result = _cancellable_executor(registry, token).execute("s1", _two_step_plan(), {"gnome.type_text"})
    assert result.success is False
    assert result.data["status"] == "cancelled"
    assert len(seen) == 1


def _cancellable_executor(registry: ToolRegistry, token: object) -> Executor:
    store = FileStore(tempfile.mkdtemp(prefix="tusk-sequence-exec-"))
    return Executor(registry, store, token)


def _two_step_plan() -> dict[str, object]:
    steps = [
        {"id": "s1", "tool_name": "gnome.type_text", "args": {"text": "one"}},
        {"id": "s2", "tool_name": "gnome.type_text", "args": {"text": "two"}},
    ]
    return {"goal": "Type twice", "steps": steps}


def _record_then_interrupt(seen: list[dict[str, object]], token: object) -> object:
    def execute(arguments: dict[str, object]) -> ToolResult:
        seen.append(dict(arguments))
        token.interrupt()
        return ToolResult(True, "typed")
    return execute


def _settle_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.launch_application", "launched", sequence_callable=True, settle_ms=2000))
    registry.register(make_registry_tool("gnome.type_text", "typed", sequence_callable=True))
    return registry


def _settling_executor(registry: ToolRegistry, sleeps: list[float]) -> Executor:
    store = FileStore(tempfile.mkdtemp(prefix="tusk-sequence-exec-"))
    return Executor(registry, store, sleep=sleeps.append)


def test_sequence_executor_settles_after_launch_style_steps() -> None:
    sleeps: list[float] = []
    steps = [
        {"id": "s1", "tool_name": "gnome.launch_application", "args": {"text": "gedit"}},
        {"id": "s2", "tool_name": "gnome.type_text", "args": {"text": "hi"}},
    ]
    plan = {"goal": "Open and type", "steps": steps}
    allowed = {"gnome.launch_application", "gnome.type_text"}
    result = _settling_executor(_settle_registry(), sleeps).execute("s1", plan, allowed)
    assert result.success is True
    assert sleeps == [2.0]


def test_sequence_executor_skips_settle_on_last_step() -> None:
    sleeps: list[float] = []
    plan = {"goal": "Open app", "steps": [{"id": "s1", "tool_name": "gnome.launch_application", "args": {"text": "gedit"}}]}
    result = _settling_executor(_settle_registry(), sleeps).execute("s1", plan, {"gnome.launch_application"})
    assert result.success is True
    assert sleeps == []
