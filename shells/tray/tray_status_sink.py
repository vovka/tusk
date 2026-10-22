from collections.abc import Callable

from shells.tray.interfaces.tray_backend import TrayBackend
from shells.tray.tray_menu_item import TrayMenuItem
from tusk.shared.interfaces.status_sink import StatusSink
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.status_snapshot import StatusSnapshot

__all__ = ["TrayStatusSink"]

Action = Callable[[], None]


class TrayStatusSink(StatusSink):
    _NAMES = {
        AppStatus.STARTING: "neutral",
        AppStatus.LISTENING: "active",
        AppStatus.REACTING: "busy",
        AppStatus.PAUSED: "muted",
        AppStatus.ERROR: "error",
        AppStatus.STOPPED: "",
    }

    def __init__(
        self,
        backend: TrayBackend,
        pause: Action | None,
        resume: Action | None,
        open_logs: Action,
        restart: Action,
        exit: Action,
        theme: str = "light",
        icon_dir: str = "shells/tray/icons",
        show_last_activity: bool = False,
        marshal: Callable[[Action], None] | None = None,
    ) -> None:
        self._backend = backend
        self._pause, self._resume = pause, resume
        self._open_logs, self._restart, self._exit = open_logs, restart, exit
        self._theme = theme
        self._icon_dir = icon_dir
        self._show_last_activity = show_last_activity
        self._marshal = marshal or (lambda render: render())
        self._last_menu: tuple[TrayMenuItem, ...] | None = None

    def publish(self, snapshot: StatusSnapshot) -> None:
        self._marshal(lambda: self._render(snapshot))

    def icon_path(self, status: AppStatus) -> str:
        name = self._NAMES[status]
        if not name:
            return ""
        return f"{self._icon_dir}/{self._theme}/{name}.png"

    def _render(self, snapshot: StatusSnapshot) -> None:
        icon = self.icon_path(snapshot.status)
        if icon:
            self._backend.set_icon(icon)
        self._backend.set_tooltip(self._tooltip(snapshot))
        self._update_menu(snapshot)

    def _update_menu(self, snapshot: StatusSnapshot) -> None:
        # Rebuilding collapses any open submenu, so only do it on real change.
        menu = self._menu(snapshot)
        if menu == self._last_menu:
            return
        self._last_menu = menu
        self._backend.set_menu(menu)

    def _tooltip(self, snapshot: StatusSnapshot) -> str:
        if snapshot.status is AppStatus.ERROR and snapshot.detail:
            return f"TUSK — error: {snapshot.detail}"
        return f"TUSK — {snapshot.status.value}{self._latency_suffix(snapshot)}"

    def _latency_suffix(self, snapshot: StatusSnapshot) -> str:
        if snapshot.latency_median_ms is None:
            return ""
        return f" — median latency {snapshot.latency_median_ms / 1000:.1f} s"

    def _menu(self, snapshot: StatusSnapshot) -> tuple[TrayMenuItem, ...]:
        return (*self._info_lines(snapshot), self._models_item(snapshot), *self._control_items(snapshot))

    def _info_lines(self, snapshot: StatusSnapshot) -> list[TrayMenuItem]:
        lines = [self._info("Mode", snapshot.mode.value)]
        if self._show_last_activity:
            lines.append(self._info("Last", snapshot.detail))
        lines.append(self._info("Mic", snapshot.mic_device))
        return lines

    def _models_item(self, snapshot: StatusSnapshot) -> TrayMenuItem:
        children = tuple(self._info(slot, model) for slot, model in snapshot.models)
        return TrayMenuItem("Models", children=children)

    def _control_items(self, snapshot: StatusSnapshot) -> list[TrayMenuItem]:
        return [
            self._pause_resume(snapshot),
            TrayMenuItem("Open logs", self._open_logs, True),
            TrayMenuItem("Restart", self._restart, True),
            TrayMenuItem("Exit", self._exit, True),
        ]

    def _pause_resume(self, snapshot: StatusSnapshot) -> TrayMenuItem:
        if snapshot.status is AppStatus.PAUSED:
            return TrayMenuItem("Resume", self._resume, True)
        return TrayMenuItem("Pause", self._pause, True)

    def _info(self, key: str, value: str) -> TrayMenuItem:
        return TrayMenuItem(f"{key}: {value}")
