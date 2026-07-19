import subprocess
import types

from adapters.gnome.tools import application_tools
from adapters.gnome.tools.application_tools import ApplicationTools

_EXISTING_WINDOW = "0x00100003 0 vovkalaptop Terminal"
_NEW_WINDOW = "0x00200007 0 vovkalaptop Text Editor"


# Regression: gedit was reported "launched" before its window mapped, so the
# agent re-launched it repeatedly and typed into the still-focused terminal.
def test_launch_application_reports_new_window_after_second_poll(monkeypatch) -> None:
    stdout_values = [_EXISTING_WINDOW, _EXISTING_WINDOW, f"{_EXISTING_WINDOW}\n{_NEW_WINDOW}"]
    monkeypatch.setattr(application_tools.subprocess, "run", _wmctrl_sequence(stdout_values))
    sleeps: list[float] = []
    tools = _tools(sleeps.append)
    result = tools.launch_application({"application_name": "gedit"})
    assert result == {"success": True, "message": 'launched: gedit, window "Text Editor" open'}
    assert sleeps == [0.5]


def test_launch_application_reports_no_new_window_within_budget(monkeypatch) -> None:
    monkeypatch.setattr(application_tools.subprocess, "run", _wmctrl_sequence([_EXISTING_WINDOW]))
    sleeps: list[float] = []
    tools = _tools(sleeps.append)
    result = tools.launch_application({"application_name": "gedit"})
    assert result == {"success": True, "message": "launched: gedit (no new window appeared within 10s)"}
    assert len(sleeps) == 20


def test_launch_application_reports_launcher_error_without_polling(monkeypatch) -> None:
    monkeypatch.setattr(application_tools.subprocess, "run", _wmctrl_sequence([_EXISTING_WINDOW]))
    tools = _tools(_unexpected_sleep, launch_response="error: launcher offline\n")
    result = tools.launch_application({"application_name": "gedit"})
    assert result == {"success": False, "message": "error: launcher offline"}


# Regression: warm/fast apps can map a window between the launcher ack and a
# post-ack snapshot, so the baseline must be taken before the launch call.
def test_launch_application_captures_window_baseline_before_launching(monkeypatch) -> None:
    call_order: list[str] = []
    stdout_values = [_EXISTING_WINDOW, f"{_EXISTING_WINDOW}\n{_NEW_WINDOW}"]
    monkeypatch.setattr(application_tools.subprocess, "run", _recording_wmctrl(call_order, stdout_values))
    tools = _tools(_unexpected_sleep)
    tools._launch = _recording_launch(call_order)
    tools.launch_application({"application_name": "gedit"})
    assert call_order == ["wmctrl", "launch", "wmctrl"]


# Regression: a non-zero wmctrl returncode can carry error text on stdout;
# that must not be misparsed as a real window.
def test_launch_application_treats_wmctrl_failure_as_no_windows(monkeypatch) -> None:
    monkeypatch.setattr(application_tools.subprocess, "run", _failing_wmctrl_after_baseline())
    sleeps: list[float] = []
    tools = _tools(sleeps.append)
    result = tools.launch_application({"application_name": "gedit"})
    assert result == {"success": True, "message": "launched: gedit (no new window appeared within 10s)"}
    assert len(sleeps) == 20


def test_launch_application_treats_missing_wmctrl_as_no_windows(monkeypatch) -> None:
    monkeypatch.setattr(application_tools.subprocess, "run", _missing_wmctrl)
    sleeps: list[float] = []
    tools = _tools(sleeps.append)
    result = tools.launch_application({"application_name": "gedit"})
    assert result == {"success": True, "message": "launched: gedit (no new window appeared within 10s)"}
    assert len(sleeps) == 20


def _wmctrl_sequence(stdout_values: list[str]) -> object:
    responses = iter(stdout_values)
    last = stdout_values[-1]

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(command, 0, next(responses, last), "")

    return fake_run


def _recording_wmctrl(call_order: list[str], stdout_values: list[str]) -> object:
    inner = _wmctrl_sequence(stdout_values)

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        call_order.append("wmctrl")
        return inner(command, **kwargs)

    return fake_run


def _recording_launch(call_order: list[str]) -> object:
    def fake_launch(application_name: str) -> str:
        call_order.append("launch")
        return "ok\n"

    return fake_launch


def _failing_wmctrl_after_baseline() -> object:
    calls: list[int] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        calls.append(1)
        if len(calls) == 1:
            return subprocess.CompletedProcess(command, 0, "", "")
        return subprocess.CompletedProcess(command, 1, "Error: Cannot connect to X server", "")

    return fake_run


def _missing_wmctrl(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
    raise FileNotFoundError("wmctrl: command not found")


def _unexpected_sleep(seconds: float) -> None:
    raise AssertionError("should not sleep on launcher error")


def _tools(sleep: object, launch_response: str = "ok\n") -> ApplicationTools:
    apps = types.SimpleNamespace(search=lambda query, limit=1: [types.SimpleNamespace(exec_cmd="gedit")])
    tools = ApplicationTools(apps, sleep=sleep)
    tools._launch = lambda application_name: launch_response  # type: ignore[method-assign]
    return tools
