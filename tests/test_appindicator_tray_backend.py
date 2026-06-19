from shells.tray.appindicator_tray_backend import AppIndicatorTrayBackend
from shells.tray.tray_menu_item import TrayMenuItem


def test_backend_sets_icon_tooltip_and_menu() -> None:
    backend = AppIndicatorTrayBackend()
    backend.set_tooltip("TUSK — listening")
    backend.set_icon("shells/tray/icons/light/active.png")
    backend.set_menu((TrayMenuItem("Models", children=(TrayMenuItem("g: m"),)),))
    assert backend._icon.title == "TUSK — listening"
    assert backend._icon.icon.path.endswith("active.png")
    assert len(backend._icon.menu.items) == 1


def test_menu_item_callback_invokes_action() -> None:
    calls: list[str] = []
    backend = AppIndicatorTrayBackend()
    backend.set_menu((TrayMenuItem("Pause", lambda: calls.append("pause"), True),))
    item = backend._icon.menu.items[0]
    item.action(None, item)
    assert calls == ["pause"]


def test_disabled_item_has_no_callback() -> None:
    backend = AppIndicatorTrayBackend()
    backend.set_menu((TrayMenuItem("Status: listening"),))
    assert backend._icon.menu.items[0].action is None
