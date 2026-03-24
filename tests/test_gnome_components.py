import types

from tusk.gnome.app_catalog import AppCatalog
from tusk.gnome.gnome_clipboard_provider import GnomeClipboardProvider
from tusk.gnome.gnome_context_provider import GnomeContextProvider
from tusk.gnome.gnome_gatekeeper import GnomeGatekeeper
from tusk.gnome.gnome_input_simulator import GnomeInputSimulator
from tusk.gnome.gnome_text_paster import GnomeTextPaster
from tusk.schemas.utterance import Utterance


def test_app_catalog_parse(tmp_path) -> None:
    desktop = tmp_path / "app.desktop"
    desktop.write_text("[Desktop Entry]\nType=Application\nName=Calc\nExec=gnome-calculator %U\n")
    apps = AppCatalog([str(tmp_path)]).list_apps()
    assert apps[0].name == "Calc" and apps[0].exec_cmd == "gnome-calculator"


def test_gnome_context_provider(monkeypatch) -> None:
    out = types.SimpleNamespace(stdout="0x1 0 1 2 3 4 host Title\n")
    monkeypatch.setattr("subprocess.run", lambda *a, **k: out if "wmctrl" in a[0] else types.SimpleNamespace(stdout="Title\n"))
    ctx = GnomeContextProvider(types.SimpleNamespace(list_apps=lambda: [])).get_context()
    assert ctx.active_window_title == "Title" and ctx.open_windows[0].x == 1


def test_gatekeeper_parsing() -> None:
    llm = types.SimpleNamespace(label="x", complete=lambda *a: '{"directed":true,"cleaned_command":"open"}')
    gate = GnomeGatekeeper(llm, types.SimpleNamespace(log=lambda *a: None))
    result = gate.evaluate(Utterance("hi", b"", 0.1), "p")
    assert result.is_directed_at_tusk and result.cleaned_command == "open"


def test_gnome_input_and_paster(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: calls.append(a[0]))
    sim = GnomeInputSimulator(); sim.press_keys("ctrl+A"); sim.mouse_scroll("up", 2)
    paster = GnomeTextPaster(); paster.paste("x"); paster.replace(1, "y")
    assert any("xdotool" in c[0] for c in calls)


def test_clipboard_provider(monkeypatch) -> None:
    monkeypatch.setattr("subprocess.run", lambda *a, **k: types.SimpleNamespace(stdout="clip"))
    clip = GnomeClipboardProvider()
    assert clip.read() == "clip"
    assert clip.write("x") is None
