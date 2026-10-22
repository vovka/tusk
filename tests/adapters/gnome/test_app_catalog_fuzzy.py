from adapters.gnome.app_catalog import AppCatalog


def _catalog(tmp_path) -> AppCatalog:
    (tmp_path / "gedit.desktop").write_text("[Desktop Entry]\nType=Application\nName=Text Editor\nExec=gedit %U\n")
    return AppCatalog([str(tmp_path)])


def test_search_falls_back_to_fuzzy_match_on_command(tmp_path) -> None:
    assert [app.exec_cmd for app in _catalog(tmp_path).search("Jetit")] == ["gedit"]


def test_search_does_not_false_match_unrelated_word(tmp_path) -> None:
    assert _catalog(tmp_path).search("banana") == []
