from adapters.gnome.app_catalog import AppCatalog
from adapters.gnome.app_vocabulary import AppVocabulary


def test_text_lists_tusk_and_installed_command_names(tmp_path) -> None:
    (tmp_path / "gedit.desktop").write_text("[Desktop Entry]\nType=Application\nName=Text Editor\nExec=/usr/bin/gedit %U\n")
    assert AppVocabulary(AppCatalog([str(tmp_path)])).text() == "TUSK, gedit"
