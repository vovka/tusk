import os
import subprocess
import sys
import threading
from collections.abc import Callable

from shells.tray.appindicator_tray_backend import AppIndicatorTrayBackend
from shells.tray.interfaces.tray_backend import TrayBackend
from shells.tray.tray_status_sink import TrayStatusSink
from shells.voice.voice_shell import VoiceShell
from tusk.shared.config.config import Config
from tusk.shared.observability.status_reporter import StatusReporter
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["TrayShell"]


class TrayShell:
    def __init__(
        self,
        reporter: StatusReporter,
        pipeline_control: VoiceShell,
        shutdown_event: threading.Event,
        config: Config,
        backend: TrayBackend | None = None,
    ) -> None:
        self._reporter = reporter
        self._control = pipeline_control
        self._shutdown_event = shutdown_event
        self._config = config
        self._backend = backend

    def start(self, submit: Callable[[str], KernelResponse]) -> None:
        backend = self._resolve_backend()
        if backend is not None:
            sink = self._sink(backend)
            self._reporter.attach_sink(sink)
            self._prime_icon(backend, sink)
            self._run_backend(backend)
        self._shutdown_event.wait()

    def stop(self) -> None:
        self._shutdown_event.set()
        if self._backend is not None:
            self._backend.stop()

    def _resolve_backend(self) -> TrayBackend | None:
        if self._backend is None:
            self._backend = self._build_backend()
        return self._backend

    def _build_backend(self) -> TrayBackend | None:
        try:
            return AppIndicatorTrayBackend()
        except (ImportError, RuntimeError):
            return None

    def _sink(self, backend: TrayBackend) -> TrayStatusSink:
        return TrayStatusSink(
            backend, self._control.pause, self._control.resume, self._open_logs, self._restart, self.stop,
            theme=self._config.tray_icon_theme,
            show_last_activity=self._config.tray_show_last_activity,
            marshal=self._marshal,
        )

    def _prime_icon(self, backend: TrayBackend, sink: TrayStatusSink) -> None:
        icon = sink.icon_path(self._reporter.status)
        if icon:
            backend.set_icon(icon)

    def _marshal(self, render: Callable[[], None]) -> None:
        try:
            from gi.repository import GLib
        except (ImportError, ValueError):
            self._safe_render(render)
            return
        GLib.idle_add(lambda: self._safe_render(render))

    def _safe_render(self, render: Callable[[], None]) -> bool:
        try:
            render()
        except Exception as exc:
            self._log_render_failure(exc)
        return False

    def _log_render_failure(self, exc: Exception) -> None:
        if hasattr(self._config, "log"):
            self._config.log("TRAY", f"tray render failed: {exc}", "tray")

    def _run_backend(self, backend: TrayBackend) -> None:
        try:
            backend.run()
        except Exception:  # a GUI-loop crash must degrade to headless, not kill daemons
            backend.stop()

    def _open_logs(self) -> None:
        if sys.platform == "win32":
            os.startfile(self._config.agent_session_log_dir)
            return
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen([opener, self._config.agent_session_log_dir])

    def _restart(self) -> None:
        os.execv(sys.executable, [sys.executable, *sys.argv])
