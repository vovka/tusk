import types

from adapters.gnome.tools.input_tools import InputTools
from adapters.gnome.tools.launched_window_guard import LaunchedWindowGuard


class _Windows:
    def __init__(self, active: str, focus_works: bool = True) -> None:
        self.active = active
        self.focused: list[str] = []
        self._focus_works = focus_works

    def active_window_id(self) -> str:
        return self.active

    def focus(self, window_id: str) -> None:
        self.focused.append(window_id)
        if self._focus_works:
            self.active = window_id


def _input_tools(guard: LaunchedWindowGuard, typed: list[str]) -> InputTools:
    simulator = types.SimpleNamespace(type_text=typed.append)
    return InputTools(simulator, guard)


def test_typing_after_launch_focuses_launched_window_first() -> None:
    windows, typed = _Windows(active="0x01"), []
    guard = LaunchedWindowGuard(windows, sleep=lambda seconds: None)
    guard.remember("0x02", "Untitled Document 1 - gedit")
    assert _input_tools(guard, typed).type_text({"text": "poem"})["success"] is True
    assert windows.focused == ["0x02"] and typed == ["poem"]


def test_typing_after_launch_refuses_when_focus_fails() -> None:
    windows, typed = _Windows(active="0x01", focus_works=False), []
    guard = LaunchedWindowGuard(windows, sleep=lambda seconds: None)
    guard.remember("0x02", "Untitled Document 1 - gedit")
    result = _input_tools(guard, typed).type_text({"text": "poem"})
    assert result["success"] is False and "Untitled Document 1 - gedit" in result["message"]
    assert typed == []


def test_guard_applies_once_and_expires() -> None:
    windows, now = _Windows(active="0x01", focus_works=False), [0.0]
    guard = LaunchedWindowGuard(windows, sleep=lambda seconds: None, clock=lambda: now[0])
    guard.remember("0x02", "gedit")
    now[0] = 61.0
    assert guard.ensure_active() is None
    guard.remember("0x02", "gedit")
    assert guard.ensure_active() is not None
    assert guard.ensure_active() is None
