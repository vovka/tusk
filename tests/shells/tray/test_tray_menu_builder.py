from shells.tray.status_icon_resolver import StatusIconResolver
from shells.tray.tray_menu_actions import TrayMenuActions
from shells.tray.tray_menu_builder import TrayMenuBuilder
from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.status_snapshot import StatusSnapshot


def _actions() -> TrayMenuActions:
    return TrayMenuActions(lambda: None, lambda: None, lambda: None, lambda: None, lambda: None)


def _labels(snapshot: StatusSnapshot, show_last: bool = False) -> list[str]:
    items = TrayMenuBuilder().build(snapshot, _actions(), show_last)
    return [item.label for item in items]


def test_menu_hides_last_activity_by_default() -> None:
    snapshot = StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT, "open Firefox", "Mic A")
    assert _labels(snapshot) == ["Mode: default", "Mic: Mic A", "Models", "Pause", "Open logs", "Restart", "Exit"]


def test_menu_omits_volatile_status_line() -> None:
    # The status line changed on every say->reply and collapsed open submenus;
    # status now lives in the icon/tooltip so the menu stays stable.
    snapshot = StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT)
    assert not any(label.startswith("Status:") for label in _labels(snapshot))


def test_menu_shows_last_activity_when_opted_in() -> None:
    snapshot = StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT, "open Firefox")
    assert "Last: open Firefox" in _labels(snapshot, show_last=True)


def test_pause_label_flips_to_resume_when_paused() -> None:
    snapshot = StatusSnapshot(AppStatus.PAUSED, AppMode.DEFAULT)
    assert "Resume" in _labels(snapshot) and "Pause" not in _labels(snapshot)


def test_pause_action_is_wired_to_pause_callable() -> None:
    calls: list[str] = []
    actions = TrayMenuActions(lambda: calls.append("pause"), lambda: None, lambda: None, lambda: None, lambda: None)
    items = TrayMenuBuilder().build(StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT), actions)
    next(item for item in items if item.label == "Pause").action()
    assert calls == ["pause"]


def test_models_submenu_lists_one_disabled_child_per_slot() -> None:
    snapshot = StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT, models=(("gatekeeper", "groq/llama"),))
    models = next(item for item in TrayMenuBuilder().build(snapshot, _actions()) if item.label == "Models")
    assert [child.label for child in models.children] == ["gatekeeper: groq/llama"]


def test_icon_resolver_maps_status_to_themed_path() -> None:
    resolver = StatusIconResolver("dark")
    assert resolver.resolve(AppStatus.LISTENING) == "shells/tray/icons/dark/active.png"
    assert resolver.resolve(AppStatus.STOPPED) == ""
