from adapters.gnome.app_catalog import AppCatalog


def test_app_catalog_parses_exec(tmp_path) -> None:
    desktop = tmp_path / "calc.desktop"
    desktop.write_text("[Desktop Entry]\nType=Application\nName=Calc\nExec=gnome-calculator %U\n")
    apps = AppCatalog([str(tmp_path)]).list_apps()
    assert apps[0].exec_cmd == "gnome-calculator"

