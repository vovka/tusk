from shells.tray.tray_menu_actions import TrayMenuActions
from shells.tray.tray_menu_item import TrayMenuItem
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.status_snapshot import StatusSnapshot

__all__ = ["TrayMenuBuilder"]


class TrayMenuBuilder:
    def build(
        self,
        snapshot: StatusSnapshot,
        actions: TrayMenuActions,
        show_last_activity: bool = False,
    ) -> tuple[TrayMenuItem, ...]:
        items = self._info_lines(snapshot, show_last_activity)
        items.append(self._models_item(snapshot))
        items.extend(self._control_items(snapshot, actions))
        return tuple(items)

    def _info_lines(self, snapshot: StatusSnapshot, show_last_activity: bool) -> list[TrayMenuItem]:
        lines = [self._status_line(snapshot), self._info("Mode", snapshot.mode.value)]
        if show_last_activity:
            lines.append(self._info("Last", snapshot.detail))
        lines.append(self._info("Mic", snapshot.mic_device))
        return lines

    def _status_line(self, snapshot: StatusSnapshot) -> TrayMenuItem:
        label = snapshot.status.value
        if snapshot.status is AppStatus.ERROR and snapshot.detail:
            label = f"{label}: {snapshot.detail}"
        return self._info("Status", label)

    def _models_item(self, snapshot: StatusSnapshot) -> TrayMenuItem:
        children = tuple(self._info(slot, model) for slot, model in snapshot.models)
        return TrayMenuItem("Models", children=children)

    def _control_items(self, snapshot: StatusSnapshot, actions: TrayMenuActions) -> list[TrayMenuItem]:
        return [
            self._pause_resume(snapshot, actions),
            TrayMenuItem("Open logs", actions.open_logs, True),
            TrayMenuItem("Restart", actions.restart, True),
            TrayMenuItem("Exit", actions.exit, True),
        ]

    def _pause_resume(self, snapshot: StatusSnapshot, actions: TrayMenuActions) -> TrayMenuItem:
        if snapshot.status is AppStatus.PAUSED:
            return TrayMenuItem("Resume", actions.resume, True)
        return TrayMenuItem("Pause", actions.pause, True)

    def _info(self, key: str, value: str) -> TrayMenuItem:
        return TrayMenuItem(f"{key}: {value}")
