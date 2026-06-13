from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.status_snapshot import StatusSnapshot
from tusk.shared.status.interfaces.status_reporter import StatusReporter
from tusk.shared.status.interfaces.status_sink import StatusSink

__all__ = ["StatusReporterHub"]


class StatusReporterHub(StatusReporter):
    def __init__(self, sink: StatusSink, log: object | None = None) -> None:
        self._sink = sink
        self._log = log
        self._status = AppStatus.STARTING
        self._mode = AppMode.DEFAULT
        self._detail = ""
        self._mic_device = ""
        self._models: tuple[tuple[str, str], ...] = ()

    @property
    def status(self) -> AppStatus:
        return self._status

    def attach_sink(self, sink: StatusSink) -> None:
        self._sink = sink
        self._emit()

    def set_status(self, status: AppStatus, detail: str = "") -> None:
        self._status = status
        self._detail = detail
        self._emit()

    def set_mode(self, mode: AppMode) -> None:
        self._mode = mode
        self._emit()

    def set_models(self, models: tuple[tuple[str, str], ...]) -> None:
        self._models = tuple(models)
        self._emit()

    def set_mic_device(self, device: str) -> None:
        self._mic_device = device
        self._emit()

    def _emit(self) -> None:
        try:
            self._sink.publish(self._snapshot())
        except Exception as exc:  # never let a broken sink reach a producer
            self._log_failure(exc)

    def _snapshot(self) -> StatusSnapshot:
        return StatusSnapshot(self._status, self._mode, self._detail, self._mic_device, self._models)

    def _log_failure(self, exc: Exception) -> None:
        if self._log is not None:
            self._log.log("TRAY", f"status sink failed: {exc}", "tray")
