import threading
import types

from shells.tray.tray_shell import TrayShell
from tusk.shared.status.null_status_sink import NullStatusSink
from tusk.shared.status.status_reporter_hub import StatusReporterHub


def _config() -> object:
    return types.SimpleNamespace(tray_icon_theme="light", tray_show_last_activity=False, conversation_log_dir="/tmp")


def _backend() -> object:
    state = types.SimpleNamespace(ran=False, stopped=False, menu=())
    state.run = lambda: setattr(state, "ran", True)
    state.stop = lambda: setattr(state, "stopped", True)
    state.set_icon = lambda value: None
    state.set_tooltip = lambda value: None
    state.set_menu = lambda items: setattr(state, "menu", items)
    return state


def _control() -> object:
    calls: list[str] = []
    return types.SimpleNamespace(calls=calls, pause=lambda: calls.append("pause"), resume=lambda: calls.append("resume"))


def test_start_attaches_sink_runs_backend_and_returns_when_shutdown_set() -> None:
    backend, control, event = _backend(), _control(), threading.Event()
    event.set()
    TrayShell(StatusReporterHub(NullStatusSink()), control, event, _config(), backend).start(lambda text: None)
    assert backend.ran and backend.menu


def test_pause_menu_item_is_wired_to_pipeline_control() -> None:
    backend, control, event = _backend(), _control(), threading.Event()
    event.set()
    TrayShell(StatusReporterHub(NullStatusSink()), control, event, _config(), backend).start(lambda text: None)
    next(item for item in backend.menu if item.label == "Pause").action()
    assert control.calls == ["pause"]


def test_gui_crash_degrades_to_headless_without_raising() -> None:
    backend = _backend()
    backend.run = _raise
    shell = TrayShell(StatusReporterHub(NullStatusSink()), _control(), threading.Event(), _config(), backend)
    shell._run_backend(backend)
    assert backend.stopped


def test_missing_backend_library_runs_no_op() -> None:
    shell = TrayShell(StatusReporterHub(NullStatusSink()), _control(), threading.Event(), _config(), backend=None)
    shell._build_backend = lambda: None
    event = threading.Event()
    event.set()
    shell._shutdown_event = event
    shell.start(lambda text: None)


def _raise() -> None:
    raise RuntimeError("gui crashed")
