import tempfile

from tests.support.kernel_api import make_registry_tool
from tusk.kernel.agent.confirmation.confirmation_gate import ConfirmationGate
from tusk.kernel.agent.session_store import SessionStore
from tusk.kernel.agent.tool_sequence.executor import Executor
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.shared.schemas.tools.tool_sequence_plan import ToolSequencePlan


def test_sequence_executor_runs_steps_in_order() -> None:
    seen: list[dict[str, object]] = []
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed", sequence_callable=True, execute=_record(seen)))
    result = _executor(registry).execute_plan("s1", ToolSequencePlan.from_dict(_plan("hello")), {"gnome.type_text"})
    assert result.success is True
    assert seen == [{"text": "hello"}]
    assert result.data["completed_step_ids"] == ["s1"]


def test_sequence_executor_aborts_on_failed_step() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed", sequence_callable=True, execute=_fail))
    result = _executor(registry).execute_plan("s1", ToolSequencePlan.from_dict(_plan("hello")), {"gnome.type_text"})
    assert result.success is False
    assert result.data["failed_step_id"] == "s1"


def test_sequence_executor_reports_invalid_plan_as_sequence_plan() -> None:
    plan = ToolSequencePlan.from_dict({"goal": "Type text", "steps": _plan("hello")["steps"] * 2})
    result = _executor(_settle_registry()).execute_plan("s1", plan, {"gnome.type_text"})
    assert (result.success, result.message) == (False, "sequence_plan contains duplicate step ids")


def _executor(registry: ToolRegistry) -> Executor:
    store = SessionStore(tempfile.mkdtemp(prefix="tusk-sequence-exec-"))
    return Executor(registry, store, confirmation=ConfirmationGate(registry))


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
    from tusk.shared.interrupt_token import InterruptToken
    token = InterruptToken()
    seen: list[dict[str, object]] = []
    registry = ToolRegistry()
    execute = _record_then_interrupt(seen, token)
    registry.register(make_registry_tool("gnome.type_text", "typed", sequence_callable=True, execute=execute))
    result = _cancellable_executor(registry, token).execute_plan("s1", ToolSequencePlan.from_dict(_two_step_plan()), {"gnome.type_text"})
    assert result.success is False
    assert result.data["status"] == "cancelled"
    assert len(seen) == 1


def _cancellable_executor(registry: ToolRegistry, token: object) -> Executor:
    store = SessionStore(tempfile.mkdtemp(prefix="tusk-sequence-exec-"))
    return Executor(registry, store, token, confirmation=ConfirmationGate(registry))


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
    store = SessionStore(tempfile.mkdtemp(prefix="tusk-sequence-exec-"))
    return Executor(registry, store, sleep=sleeps.append, confirmation=ConfirmationGate(registry))


def test_sequence_executor_settles_after_launch_style_steps() -> None:
    sleeps: list[float] = []
    steps = [
        {"id": "s1", "tool_name": "gnome.launch_application", "args": {"text": "gedit"}},
        {"id": "s2", "tool_name": "gnome.type_text", "args": {"text": "hi"}},
    ]
    plan = {"goal": "Open and type", "steps": steps}
    allowed = {"gnome.launch_application", "gnome.type_text"}
    result = _settling_executor(_settle_registry(), sleeps).execute_plan("s1", ToolSequencePlan.from_dict(plan), allowed)
    assert result.success is True
    assert sleeps == [2.0]


def test_sequence_executor_skips_settle_on_last_step() -> None:
    sleeps: list[float] = []
    plan = {"goal": "Open app", "steps": [{"id": "s1", "tool_name": "gnome.launch_application", "args": {"text": "gedit"}}]}
    result = _settling_executor(_settle_registry(), sleeps).execute_plan("s1", ToolSequencePlan.from_dict(plan), {"gnome.launch_application"})
    assert result.success is True
    assert sleeps == []


def test_sequence_executor_stops_at_destructive_step() -> None:
    seen: list[dict[str, object]] = []
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.close_window", "closed", sequence_callable=True, execute=_record(seen)))
    plan = {"goal": "Close", "steps": [{"id": "s1", "tool_name": "gnome.close_window", "args": {"window_title": "X"}}]}
    result = _executor(registry).execute_plan("s1", ToolSequencePlan.from_dict(plan), {"gnome.close_window"})
    assert result.success is False
    assert "needs_confirmation" in result.message
    assert seen == []
