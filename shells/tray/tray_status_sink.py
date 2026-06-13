from collections.abc import Callable

from shells.tray.status_icon_resolver import StatusIconResolver
from shells.tray.tray_menu_actions import TrayMenuActions
from shells.tray.tray_menu_builder import TrayMenuBuilder
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.status_snapshot import StatusSnapshot
from tusk.shared.status.interfaces.status_sink import StatusSink

__all__ = ["TrayStatusSink"]


class TrayStatusSink(StatusSink):
    def __init__(
        self,
        backend: object,
        icon_resolver: StatusIconResolver,
        menu_builder: TrayMenuBuilder,
        actions: TrayMenuActions,
        show_last_activity: bool = False,
        marshal: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self._backend = backend
        self._icons = icon_resolver
        self._menu_builder = menu_builder
        self._actions = actions
        self._show_last_activity = show_last_activity
        self._marshal = marshal or (lambda render: render())

    def publish(self, snapshot: StatusSnapshot) -> None:
        self._marshal(lambda: self._render(snapshot))

    def _render(self, snapshot: StatusSnapshot) -> None:
        icon = self._icons.resolve(snapshot.status)
        if icon:
            self._backend.set_icon(icon)
        self._backend.set_tooltip(self._tooltip(snapshot))
        self._backend.set_menu(self._menu_builder.build(snapshot, self._actions, self._show_last_activity))

    def _tooltip(self, snapshot: StatusSnapshot) -> str:
        if snapshot.status is AppStatus.ERROR and snapshot.detail:
            return f"TUSK — error: {snapshot.detail}"
        return f"TUSK — {snapshot.status.value}"
