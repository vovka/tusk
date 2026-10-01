import types

from tests.kernel_api_support import make_registry_tool
from tusk.kernel.agent.confirmation.confirmation_gate import ConfirmationGate
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_result import ToolResult


class _Desktop:
    def __init__(self) -> None:
        self.active_title = "Code"
        self.calls: list[tuple[str, dict]] = []

    def registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        for name in ("gnome.close_window", "gnome.press_keys", "gnome.focus_window"):
            registry.register(make_registry_tool(name, "ok", execute=self._recorder(name)))
        registry.register(make_registry_tool("gnome.get_active_window", "", execute=self._active))
        return registry

    def _recorder(self, name: str) -> object:
        return lambda arguments: self._record(name, arguments)

    def _record(self, name: str, arguments: dict) -> ToolResult:
        self.calls.append((name, dict(arguments)))
        return ToolResult(True, "ok")

    def _active(self, arguments: dict) -> ToolResult:
        return ToolResult(True, f"active window: {self.active_title} -> code [10x10 at 0,0]")


def _gate(desktop: _Desktop, now: list[float] | None = None) -> ConfirmationGate:
    now = now or [100.0]
    return ConfirmationGate(desktop.registry(), clock=lambda: now[0])


def test_destructive_call_is_held_with_question() -> None:
    desktop = _Desktop()
    gate = _gate(desktop)
    result = gate.execute("gnome.close_window", {"window_title": "Terminal"})
    assert result.success is False
    assert result.message.startswith("needs_confirmation: Close window 'Terminal'? Say yes to confirm.")
    assert desktop.calls == []
    assert gate.take_question() == "Close window 'Terminal'? Say yes to confirm."
    assert gate.take_question() is None


def test_safe_call_runs_directly() -> None:
    desktop = _Desktop()
    assert _gate(desktop).execute("gnome.focus_window", {"window_title": "Code"}).success is True
    assert desktop.calls == [("gnome.focus_window", {"window_title": "Code"})]


def test_yes_executes_pending_action_once() -> None:
    desktop = _Desktop()
    gate = _gate(desktop)
    gate.execute("gnome.close_window", {"window_title": "Terminal"})
    assert gate.resolve("Yes.").handled is True
    assert desktop.calls == [("gnome.close_window", {"window_title": "Terminal"})]
    assert gate.resolve("yes") is None


def test_other_utterance_cancels_pending_action() -> None:
    desktop = _Desktop()
    gate = _gate(desktop)
    gate.execute("gnome.close_window", {"window_title": "Terminal"})
    assert gate.resolve("open firefox") is None
    assert gate.resolve("yes") is None
    assert desktop.calls == []


def test_no_cancels_with_reply() -> None:
    gate = _gate(_Desktop())
    gate.execute("gnome.close_window", {"window_title": "Terminal"})
    assert gate.resolve("no").reply == "Cancelled."


def test_expired_pending_action_is_dropped() -> None:
    desktop, now = _Desktop(), [100.0]
    gate = _gate(desktop, now)
    gate.execute("gnome.close_window", {"window_title": "Terminal"})
    now[0] += 31
    assert gate.resolve("yes") is None
    assert desktop.calls == []


def test_key_press_targets_active_window_and_refuses_after_focus_change() -> None:
    desktop = _Desktop()
    gate = _gate(desktop)
    assert "Press Delete in window 'Code'?" in gate.execute("gnome.press_keys", {"keys": "Delete"}).message
    desktop.active_title = "Terminal"
    assert "no longer" in gate.resolve("confirm").reply
    assert desktop.calls == []


def test_key_press_runs_when_active_window_unchanged() -> None:
    desktop = _Desktop()
    gate = _gate(desktop)
    gate.execute("gnome.press_keys", {"keys": "Delete"})
    gate.resolve("yes")
    assert desktop.calls == [("gnome.press_keys", {"keys": "Delete"})]


def test_refuses_without_target_window() -> None:
    desktop = _Desktop()
    desktop.active_title = ""
    gate = _gate(desktop)
    result = gate.execute("gnome.press_keys", {"keys": "Delete"})
    assert result.success is False and "target window" in result.message
    assert gate.resolve("yes") is None


def test_every_tool_call_is_reported_to_latency_meter() -> None:
    marks: list[str] = []
    meter = types.SimpleNamespace(mark_tool_call=lambda: marks.append("tool"))
    gate = ConfirmationGate(_Desktop().registry(), latency_meter=meter)
    gate.execute("gnome.focus_window", {"window_title": "Code"})
    gate.execute("gnome.close_window", {"window_title": "Terminal"})
    assert marks == ["tool", "tool"]
