import subprocess

from adapters.gnome.gnome_context_provider import GnomeContextProvider

WMCTRL_LINE = "0x02e00004 -1 10 20 800 600 VovkaLaptop Системний монітор"


class StubAppCatalog:
    def list_apps(self) -> list[object]:
        return []


def _fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
    if command[0] == "wmctrl":
        return subprocess.CompletedProcess(command, 0, WMCTRL_LINE + "\n", "")
    return subprocess.CompletedProcess(command, 0, "Системний монітор\n", "")


def test_list_windows_keeps_full_multi_word_title(monkeypatch) -> None:
    """`wmctrl -l -G` has 7 columns before the title; splitting one column too
    far drops every title word but the last (codex saw 'монітор')."""
    monkeypatch.setattr(subprocess, "run", _fake_run)

    context = GnomeContextProvider(StubAppCatalog()).get_context()

    assert context.open_windows[0].title == "Системний монітор"
    assert context.open_windows[0].width == 800
    assert context.open_windows[0].height == 600
