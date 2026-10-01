from pathlib import Path

from adapters.gnome.app_catalog import AppCatalog
from adapters.gnome.app_vocabulary import AppVocabulary

_FIXTURES = str(Path(__file__).parent / "fixtures" / "xfce_apps")


def _entry(tmp_path, file_name: str, body: str) -> None:
    (tmp_path / file_name).write_text(f"[Desktop Entry]\nType=Application\n{body}\n")


def test_text_lists_tusk_and_user_facing_names_without_settings_panels() -> None:
    text = AppVocabulary(AppCatalog([_FIXTURES])).text()
    assert text == "TUSK, gedit, Thunar File Manager, Vim, Visual Studio Code"


def test_text_deduplicates_and_caps_names(tmp_path) -> None:
    for index in range(30):
        _entry(tmp_path, f"app{index:02}.desktop", f"Name=App {index:02}\nExec=app{index}")
    _entry(tmp_path, "dup.desktop", "Name=app 00\nExec=other")
    _entry(tmp_path, "prefs.desktop", "Name=Mouse Preferences\nExec=mouse-prefs")
    names = AppVocabulary(AppCatalog([str(tmp_path)])).text().split(", ")
    assert names[:3] == ["TUSK", "App 00", "App 01"] and len(names) == 26
    assert "Mouse Preferences" not in names


def test_stt_prompt_is_wake_word_only_unless_app_vocabulary_enabled() -> None:
    vocabulary = AppVocabulary(AppCatalog([_FIXTURES]))
    assert vocabulary.stt_prompt(enabled=False) == "TUSK"
    assert vocabulary.stt_prompt(enabled=True) == vocabulary.text()
