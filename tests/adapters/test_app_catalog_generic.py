from adapters.gnome.app_catalog import AppCatalog
from adapters.gnome.tools.application_tools import ApplicationTools

_ENTRIES = {
    "org.gnome.gedit.desktop": "Name=gedit\nGenericName=Text Editor\nKeywords=Notepad;Plaintext;\n"
    "Categories=Utility;TextEditor;\nExec=gedit %U",
    "kate.desktop": "Name=Kate\nGenericName=Advanced Text Editor\nCategories=Utility;TextEditor;\nExec=kate",
    "mousepad.desktop": "Name=Mousepad\nGenericName=Text Editor\nCategories=Utility;TextEditor;\nExec=mousepad",
    "firefox.desktop": "Name=Firefox\nGenericName=Web Browser\nCategories=Network;WebBrowser;\nExec=firefox %u",
    "chromium.desktop": "Name=Chromium\nGenericName=Web Browser\nCategories=Network;WebBrowser;\nExec=chromium",
    "ptyxis.desktop": "Name=Ptyxis\nCategories=System;TerminalEmulator;\nExec=ptyxis",
}


def _catalog(tmp_path, defaults: dict[str, str] | None = None) -> AppCatalog:
    for file_name, body in _ENTRIES.items():
        (tmp_path / file_name).write_text(f"[Desktop Entry]\nType=Application\n{body}\n")
    return AppCatalog([str(tmp_path)], default_app=lambda category: (defaults or {}).get(category))


def _commands(apps) -> list[str]:
    return [app.exec_cmd for app in apps]


def test_exact_name_beats_generic_name(tmp_path) -> None:
    assert _commands(_catalog(tmp_path).search("kate"))[0] == "kate"


def test_generic_name_resolves_with_stable_order(tmp_path) -> None:
    assert _commands(_catalog(tmp_path).search("text editor", limit=1)) == ["gedit"]


def test_generic_name_prefers_system_default(tmp_path) -> None:
    catalog = _catalog(tmp_path, {"TextEditor": "mousepad.desktop"})
    assert _commands(catalog.search("Text Editor", limit=1)) == ["mousepad"]


def test_keyword_resolves(tmp_path) -> None:
    assert _commands(_catalog(tmp_path).search("notepad", limit=1)) == ["gedit"]


def test_category_word_resolves_with_default(tmp_path) -> None:
    catalog = _catalog(tmp_path, {"WebBrowser": "chromium.desktop"})
    assert _commands(catalog.search("browser", limit=1)) == ["chromium"]
    assert _commands(_catalog(tmp_path).search("terminal", limit=1)) == ["ptyxis"]


def test_launch_no_match_lists_close_candidates(tmp_path) -> None:
    tools = ApplicationTools(_catalog(tmp_path), sleep=lambda _: None, window_lister=lambda: [])
    result = tools.launch_application({"application_name": "chrome"})
    assert result["success"] is False
    assert "chromium" in result["message"]


def test_suggest_caps_at_five(tmp_path) -> None:
    assert len(_catalog(tmp_path).suggest("e", limit=5)) <= 5
