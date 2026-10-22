import subprocess

import adapters.gnome.x11.x11_windows as x11_windows_module
from adapters.gnome.x11.x11_windows import X11Windows

_OUTPUTS = {
    "wmctrl": "0x0420000a  0 gedit.Gedit  box Untitled Document 1 - gedit\n0x01e00004  0 N/A  box Desktop\n",
    "xdotool": "69206026\n",
}


def _fake_run(calls: list[list[str]]) -> object:
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, _OUTPUTS.get(command[0], ""), "")
    return run


def test_lists_windows_with_wm_class_and_reads_active_id(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(x11_windows_module.subprocess, "run", _fake_run(calls))
    windows = X11Windows()
    assert windows.list_windows()[0] == ("0x0420000a", "Untitled Document 1 - gedit", "gedit.Gedit")
    assert windows.active_window_id() == "0x0420000a"
    windows.focus("0x0420000a")
    assert calls[-1] == ["wmctrl", "-i", "-a", "0x0420000a"]
