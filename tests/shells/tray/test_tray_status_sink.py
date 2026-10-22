import types

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


def _sink(backend: object, show_last: bool = False, pause=lambda: None, **kwargs) -> TrayStatusSink:
    return TrayStatusSink(
        backend, pause, lambda: None, lambda: None, lambda: None, lambda: None,
        show_last_activity=show_last, **kwargs,
    )


def _labels(snapshot: StatusSnapshot, show_last: bool = False) -> list[str]:
    backend = _backend()
    _sink(backend, show_last).publish(snapshot)
    return [item.label for item in backend.calls["menu"]]


def test_publish_renders_icon_tooltip_and_menu() -> None:
    backend = _backend()
    _sink(backend).publish(StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT, mic_device="Mic A"))
    assert backend.calls["icon"] == "shells/tray/icons/light/active.png"
    assert backend.calls["tooltip"] == "TUSK — listening"
    assert backend.calls["menu"][0].label == "Mode: default"


def test_icon_path_maps_status_to_themed_path() -> None:
    sink = _sink(_backend(), theme="dark")
    assert sink.icon_path(AppStatus.LISTENING) == "shells/tray/icons/dark/active.png"
    assert sink.icon_path(AppStatus.STOPPED) == ""


def test_error_detail_surfaces_in_tooltip() -> None:
    backend = _backend()
    _sink(backend).publish(StatusSnapshot(AppStatus.ERROR, AppMode.DEFAULT, "stt timeout"))
    assert backend.calls["tooltip"] == "TUSK — error: stt timeout"


def test_publish_uses_injected_marshal_to_defer_render() -> None:
    backend = _backend()
    queued: list = []
    _sink(backend, marshal=queued.append).publish(StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT))
    assert backend.calls == {} and len(queued) == 1


def test_stopped_status_does_not_set_icon() -> None:
    backend = _backend()
    _sink(backend).publish(StatusSnapshot(AppStatus.STOPPED, AppMode.DEFAULT))
    assert "icon" not in backend.calls


def test_menu_hides_last_activity_by_default() -> None:
    snapshot = StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT, "open Firefox", "Mic A")
    assert _labels(snapshot) == ["Mode: default", "Mic: Mic A", "Models", "Pause", "Open logs", "Restart", "Exit"]


def test_menu_shows_last_activity_when_opted_in() -> None:
    snapshot = StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT, "open Firefox")
    assert "Last: open Firefox" in _labels(snapshot, show_last=True)


def test_pause_label_flips_to_resume_when_paused() -> None:
    labels = _labels(StatusSnapshot(AppStatus.PAUSED, AppMode.DEFAULT))
    assert "Resume" in labels and "Pause" not in labels


def test_pause_action_is_wired_to_pause_callable() -> None:
    calls: list[str] = []
    backend = _backend()
    _sink(backend, pause=lambda: calls.append("pause")).publish(StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT))
    next(item for item in backend.calls["menu"] if item.label == "Pause").action()
    assert calls == ["pause"]


def test_models_submenu_lists_one_disabled_child_per_slot() -> None:
    backend = _backend()
    snapshot = StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT, models=(("gatekeeper", "groq/llama"),))
    _sink(backend).publish(snapshot)
    models = next(item for item in backend.calls["menu"] if item.label == "Models")
    assert [child.label for child in models.children] == ["gatekeeper: groq/llama"]


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


def test_latency_median_surfaces_in_tooltip() -> None:
    backend = _backend()
    _sink(backend).publish(StatusSnapshot(AppStatus.LISTENING, AppMode.DEFAULT, latency_median_ms=1400))
    assert backend.calls["tooltip"] == "TUSK — listening — median latency 1.4 s"
