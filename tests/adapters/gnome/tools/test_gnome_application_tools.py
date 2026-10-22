import types

from adapters.gnome.tools.application_tools import ApplicationTools
from adapters.gnome.tools.launched_window_guard import LaunchedWindowGuard

_TERMINAL = ("0x01", "Terminal", "xfce4-terminal.Xfce4-terminal")
_GEDIT = ("0x02", "Untitled Document 1 - gedit", "gedit.Gedit")
_TRASH = ("0x03", "Trash - Thunar", "thunar.Thunar")
_GEDIT_APP = types.SimpleNamespace(name="gedit", exec_cmd="gedit", desktop_id="org.gnome.gedit.desktop")


def _tools(listings: list[list[tuple[str, str, str]]], sleep: object = lambda seconds: None, **kwargs: object):
    responses = iter(listings)
    apps = types.SimpleNamespace(search=lambda query, limit=1: [_GEDIT_APP])
    tools = ApplicationTools(apps, sleep=sleep, window_lister=lambda: next(responses, listings[-1]), **kwargs)
    tools._launch = lambda command: "ok\n"  # type: ignore[method-assign]
    return tools


# Regression: gedit was reported "launched" before its window mapped, so the
# agent re-launched it repeatedly and typed into the still-focused terminal.
def test_launch_reports_new_app_window_after_second_poll() -> None:
    sleeps: list[float] = []
    tools = _tools([[_TERMINAL], [_TERMINAL], [_TERMINAL, _GEDIT]], sleeps.append)
    result = tools.launch_application({"application_name": "text editor"})
    assert result == {"success": True, "message": f'launched: text editor, window "{_GEDIT[1]}" of gedit open'}
    assert sleeps == [0.5]


# Regression: a Thunar Trash window appeared and was reported as the launched editor.
def test_launch_fails_when_only_another_apps_window_appears() -> None:
    sleeps: list[float] = []
    result = _tools([[_TERMINAL], [_TERMINAL, _TRASH]], sleeps.append).launch_application({"application_name": "gedit"})
    assert result["success"] is False
    assert result["message"] == (
        'launched gedit but no gedit window appeared within 10s; other new windows: "Trash - Thunar" (thunar.Thunar)'
    )
    assert len(sleeps) == 20


def test_launch_accepts_existing_app_window_of_single_instance_app() -> None:
    result = _tools([[_TERMINAL, _GEDIT]]).launch_application({"application_name": "gedit"})
    assert result["success"] is True and _GEDIT[1] in result["message"]


def test_launch_remembers_window_for_typing() -> None:
    windows = types.SimpleNamespace(active_window_id=lambda: "0x02", focus=lambda window_id: None)
    guard = LaunchedWindowGuard(windows, sleep=lambda seconds: None)
    _tools([[_TERMINAL], [_TERMINAL, _GEDIT]], launched=guard).launch_application({"application_name": "gedit"})
    assert guard.ensure_active() is None


def test_launch_reports_launcher_error_without_polling() -> None:
    tools = _tools([[_TERMINAL]], _unexpected_sleep)
    tools._launch = lambda command: "error: launcher offline\n"  # type: ignore[method-assign]
    assert tools.launch_application({"application_name": "gedit"}) == {"success": False, "message": "error: launcher offline"}


# Regression: warm/fast apps can map a window between the launcher ack and a
# post-ack snapshot, so the baseline must be taken before the launch call.
def test_launch_captures_window_baseline_before_launching() -> None:
    call_order: list[str] = []
    listings = iter([[_TERMINAL], [_TERMINAL, _GEDIT]])
    apps = types.SimpleNamespace(search=lambda query, limit=1: [_GEDIT_APP])
    tools = ApplicationTools(apps, sleep=_unexpected_sleep, window_lister=lambda: call_order.append("list") or next(listings))
    tools._launch = lambda command: call_order.append("launch") or "ok\n"  # type: ignore[method-assign]
    tools.launch_application({"application_name": "gedit"})
    assert call_order == ["list", "launch", "list"]


def _unexpected_sleep(seconds: float) -> None:
    raise AssertionError("should not sleep")
