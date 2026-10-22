from pathlib import Path

from adapters.gnome.app_catalog import AppCatalog

_FIXTURES = str(Path(__file__).parent / "fixtures" / "xfce_apps")
_DEFAULTS = {"TextEditor": "org.gnome.gedit.desktop", "FileManager": "thunar.desktop"}


def _catalog() -> AppCatalog:
    return AppCatalog([_FIXTURES], default_app=_DEFAULTS.get)


def test_text_editor_resolves_to_system_default_gedit() -> None:
    assert [app.exec_cmd for app in _catalog().search("text editor", limit=1)] == ["gedit"]


def test_file_manager_resolves_to_thunar_entry_not_action() -> None:
    assert [app.exec_cmd for app in _catalog().search("file manager", limit=1)] == ["thunar"]


def test_only_desktop_entry_group_is_parsed() -> None:
    names = {app.name: app.exec_cmd for app in _catalog().list_apps()}
    assert names["gedit"] == "gedit"
    assert names["Thunar File Manager"] == "thunar"
    assert "Trash" not in names and "New Document" not in names


def test_hidden_entries_are_skipped() -> None:
    assert "Hidden Helper" not in {app.name for app in _catalog().list_apps()}
