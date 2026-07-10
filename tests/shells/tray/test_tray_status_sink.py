import types

from shells.tray.status_icon_resolver import StatusIconResolver
from shells.tray.tray_menu_actions import TrayMenuActions
from shells.tray.tray_menu_builder import TrayMenuBuilder
from shells.tray.tray_status_sink import TrayStatusSink
from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.status_snapshot import StatusSnapshot


def _backend() -> object:
    calls: dict = {}
    return types.SimpleNamespace(
        calls=calls,
        set_icon=lambda value: calls.__setitem__("icon", value),
        set_tooltip=lambda value: calls.__setitem__("tooltip", value),
        set_menu=lambda value: calls.__setitem__("menu", value),
    )


def _actions() -> TrayMenuActions:
    return TrayMenuActions(lambda: None, lambda: None, lambda: None, lambda: None, lambda: None)


def _sink(backend: object) -> TrayStatusSink:
    return TrayStatusSink(backend, StatusIconResolver("light"), TrayMenuBuilder(), _actions())


def test_publish_renders_icon_tooltip_and_menu() -> None:
    backend = _backend()
    _sink(backend).publish(StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT, mic_device="Mic A"))
    assert backend.calls["icon"] == "shells/tray/icons/light/active.png"
    assert backend.calls["tooltip"] == "TUSK — listening"
    assert backend.calls["menu"][0].label == "Mode: default"


def test_error_detail_surfaces_in_tooltip() -> None:
    backend = _backend()
    _sink(backend).publish(StatusSnapshot(AppStatus.ERROR, AppMode.DEFAULT, "stt timeout"))
    assert backend.calls["tooltip"] == "TUSK — error: stt timeout"


def test_publish_uses_injected_marshal_to_defer_render() -> None:
    backend = _backend()
    queued: list = []
    sink = TrayStatusSink(backend, StatusIconResolver("light"), TrayMenuBuilder(), _actions(), marshal=queued.append)
    sink.publish(StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT))
    assert backend.calls == {} and len(queued) == 1


def test_stopped_status_does_not_set_icon() -> None:
    backend = _backend()
    _sink(backend).publish(StatusSnapshot(AppStatus.STOPPED, AppMode.DEFAULT))
    assert "icon" not in backend.calls


def _counting_backend() -> object:
    counts = {"menu": 0}
    return types.SimpleNamespace(
        counts=counts,
        set_icon=lambda value: None,
        set_tooltip=lambda value: None,
        set_menu=lambda value: counts.__setitem__("menu", counts["menu"] + 1),
    )


def test_unchanged_snapshot_does_not_rebuild_menu() -> None:
    backend = _counting_backend()
    sink = _sink(backend)
    sink.publish(StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT))
    sink.publish(StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT))
    assert backend.counts["menu"] == 1


def test_status_flip_does_not_rebuild_menu() -> None:
    # say -> reply flips LISTENING -> REACTING; the menu must stay put so an
    # open submenu does not collapse. Status is shown by the icon/tooltip only.
    backend = _counting_backend()
    sink = _sink(backend)
    sink.publish(StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT))
    sink.publish(StatusSnapshot(AppStatus.REACTING, AppMode.DEFAULT))
    assert backend.counts["menu"] == 1


def test_menu_structure_change_rebuilds_menu() -> None:
    backend = _counting_backend()
    sink = _sink(backend)
    sink.publish(StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT))
    sink.publish(StatusSnapshot(AppStatus.PAUSED, AppMode.DEFAULT))
    assert backend.counts["menu"] == 2
