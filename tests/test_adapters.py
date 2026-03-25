from adapters.dictation.session_response import DictationEdit
from adapters.gnome.app_catalog import AppCatalog


def test_app_catalog_parses_exec(tmp_path) -> None:
    desktop = tmp_path / "calc.desktop"
    desktop.write_text("[Desktop Entry]\nType=Application\nName=Calc\nExec=gnome-calculator %U\n")
    apps = AppCatalog([str(tmp_path)]).list_apps()
    assert apps[0].exec_cmd == "gnome-calculator"


def test_dictation_edit_defaults() -> None:
    edit = DictationEdit("insert", "hello")
    assert edit.replace_chars == 0
