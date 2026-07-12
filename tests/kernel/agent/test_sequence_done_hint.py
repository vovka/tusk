import tempfile
import types

from tests.kernel_api_support import make_registry_tool
from tusk.kernel.agent.session.file_store import FileStore
from tusk.kernel.agent.tool_sequence.executor import Executor
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_result import ToolResult


def test_success_message_prompts_the_done_tool() -> None:
    store, _events = _capturing_store()
    result = Executor(_typing_registry(), store).execute("s1", _plan(), {"gnome.type_text"})
    assert result.success is True
    assert "call the done tool" in result.message.lower()


def test_success_recorded_summary_stays_plain() -> None:
    store, events = _capturing_store()
    Executor(_typing_registry(), store).execute("s1", _plan(), {"gnome.type_text"})
    assert _finished_summary(events) == "Type text completed"


def test_failed_message_omits_the_done_prompt() -> None:
    result = Executor(_typing_registry(_fail), _file_store()).execute("s1", _plan(), {"gnome.type_text"})
    assert result.success is False
    assert "call the done tool" not in result.message.lower()


def _typing_registry(execute: object = None) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed", sequence_callable=True, execute=execute))
    return registry


def _capturing_store() -> tuple[object, list[tuple[str, str, dict[str, object]]]]:
    events: list[tuple[str, str, dict[str, object]]] = []
    store = types.SimpleNamespace(append_event=lambda sid, name, data: events.append((sid, name, data)))
    return store, events


def _finished_summary(events: list[tuple[str, str, dict[str, object]]]) -> str:
    return [data["summary"] for _, name, data in events if name == "sequence_finished"][0]


def _file_store() -> FileStore:
    return FileStore(tempfile.mkdtemp(prefix="tusk-done-hint-"))


def _plan() -> dict[str, object]:
    step = {"id": "s1", "tool_name": "gnome.type_text", "args": {"text": "hi"}}
    return {"goal": "Type text", "steps": [step]}


def _fail(arguments: dict[str, object]) -> ToolResult:
    return ToolResult(False, "boom")
