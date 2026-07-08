import os
import subprocess
import sys

from shells.tray.appindicator_tray_backend import AppIndicatorTrayBackend
from shells.tray.status_icon_resolver import StatusIconResolver
from shells.tray.tray_menu_actions import TrayMenuActions
from shells.tray.tray_menu_builder import TrayMenuBuilder
from shells.tray.tray_status_sink import TrayStatusSink

__all__ = ["TrayShell"]


class TrayShell:
    def __init__(
        self,
        reporter: object,
        pipeline_control: object,
        shutdown_event: object,
        config: object,
        backend: object | None = None,
    ) -> None:
        self._reporter = reporter
        self._control = pipeline_control
        self._shutdown_event = shutdown_event
        self._config = config
        self._backend = backend

    def start(self, submit: object) -> None:
        backend = self._resolve_backend()
        if backend is not None:
            self._attach(backend)
            self._prime_icon(backend)
            self._run_backend(backend)
        self._shutdown_event.wait()

    def stop(self) -> None:
        self._shutdown_event.set()
        if self._backend is not None:
            self._backend.stop()

    def _resolve_backend(self) -> object | None:
        if self._backend is None:
            self._backend = self._build_backend()
        return self._backend

    def _build_backend(self) -> object | None:
        try:
            return AppIndicatorTrayBackend()
        except (ImportError, RuntimeError):
            return None

    def _attach(self, backend: object) -> None:
        sink = TrayStatusSink(
            backend, self._resolver(), TrayMenuBuilder(), self._actions(),
            self._config.tray_show_last_activity, self._marshal,
        )
        self._reporter.attach_sink(sink)

    def _resolver(self) -> StatusIconResolver:
        return StatusIconResolver(self._config.tray_icon_theme)

    def _prime_icon(self, backend: object) -> None:
        icon = self._resolver().resolve(self._reporter.status)
        if icon:
            backend.set_icon(icon)

    def _marshal(self, render: object) -> None:
        try:
            from gi.repository import GLib
        except (ImportError, ValueError):
            self._safe_render(render)
            return
        GLib.idle_add(lambda: self._safe_render(render))

    def _safe_render(self, render: object) -> bool:
        try:
            render()
        except Exception as exc:
            self._log_render_failure(exc)
        return False

    def _log_render_failure(self, exc: Exception) -> None:
        if hasattr(self._config, "log"):
            self._config.log("TRAY", f"tray render failed: {exc}", "tray")

    def _run_backend(self, backend: object) -> None:
        try:
            backend.run()
        except Exception:  # a GUI-loop crash must degrade to headless, not kill daemons
            backend.stop()

    def _actions(self) -> TrayMenuActions:
        return TrayMenuActions(self._control.pause, self._control.resume, self._open_logs, self._restart, self.stop)

    def _open_logs(self) -> None:
        if sys.platform == "win32":
            os.startfile(self._config.agent_session_log_dir)
            return
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen([opener, self._config.agent_session_log_dir])

    def _restart(self) -> None:
        os.execv(sys.executable, [sys.executable, *sys.argv])
