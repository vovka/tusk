import types

from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.status_snapshot import StatusSnapshot
from tusk.shared.status.null_status_sink import NullStatusSink
from tusk.shared.status.status_reporter_hub import StatusReporterHub


def _recording_sink() -> tuple[object, list[StatusSnapshot]]:
    published: list[StatusSnapshot] = []
    return types.SimpleNamespace(publish=published.append), published


def test_hub_starts_in_starting_status() -> None:
    hub = StatusReporterHub(NullStatusSink())
    assert hub.status == AppStatus.STARTING


def test_set_status_publishes_snapshot_with_detail() -> None:
    sink, published = _recording_sink()
    StatusReporterHub(sink).set_status(AppStatus.REACTING, "open Firefox")
    assert published[-1] == StatusSnapshot(AppStatus.REACTING, AppMode.DEFAULT, "open Firefox")


def test_set_mode_and_models_accumulate_into_snapshot() -> None:
    sink, published = _recording_sink()
    hub = StatusReporterHub(sink)
    hub.set_mode(AppMode.DICTATION)
    hub.set_models((("gatekeeper", "groq/llama"),))
    assert published[-1] == StatusSnapshot(AppStatus.STARTING, AppMode.DICTATION, "", "", (("gatekeeper", "groq/llama"),))


def test_attach_sink_emits_current_snapshot() -> None:
    sink, published = _recording_sink()
    hub = StatusReporterHub(NullStatusSink())
    hub.set_mic_device("USB Mic")
    hub.attach_sink(sink)
    assert published == [StatusSnapshot(AppStatus.STARTING, AppMode.DEFAULT, "", "USB Mic", ())]


def test_sink_exception_never_propagates_and_is_logged() -> None:
    logs: list[tuple] = []
    sink = types.SimpleNamespace(publish=_raise)
    hub = StatusReporterHub(sink, types.SimpleNamespace(log=lambda *args: logs.append(args)))
    hub.set_status(AppStatus.ERROR, "boom")
    assert logs and logs[0][0] == "TRAY"


def _raise(snapshot: object) -> None:
    raise RuntimeError("gui down")


def test_unchanged_status_is_not_published_again() -> None:
    sink, published = _recording_sink()
    hub = StatusReporterHub(sink)
    hub.set_status(AppStatus.LISTENING)
    hub.set_status(AppStatus.LISTENING)
    assert len(published) == 1
