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
    monkeypatch.setattr(application_tools.subprocess, "run", _unexpected_wmctrl_call)
    tools = _tools(_unexpected_sleep, launch_response="error: launcher offline\n")
    result = tools.launch_application({"application_name": "gedit"})
    assert result == {"success": False, "message": "error: launcher offline"}


def _wmctrl_sequence(stdout_values: list[str]) -> object:
    responses = iter(stdout_values)
    last = stdout_values[-1]

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(command, 0, next(responses, last), "")

    return fake_run


def _unexpected_wmctrl_call(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
    raise AssertionError("wmctrl should not be called on launcher error")


def _unexpected_sleep(seconds: float) -> None:
    raise AssertionError("should not sleep on launcher error")


def _tools(sleep: object, launch_response: str = "ok\n") -> ApplicationTools:
    apps = types.SimpleNamespace(search=lambda query, limit=1: [types.SimpleNamespace(exec_cmd="gedit")])
    tools = ApplicationTools(apps, sleep=sleep)
    tools._launch = lambda application_name: launch_response  # type: ignore[method-assign]
    return tools
