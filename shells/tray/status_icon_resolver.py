from tusk.shared.schemas.app_status import AppStatus

__all__ = ["StatusIconResolver"]


class StatusIconResolver:
    _NAMES = {
        AppStatus.STARTING: "neutral",
        AppStatus.LISTENING: "active",
        AppStatus.REACTING: "busy",
        AppStatus.PAUSED: "muted",
        AppStatus.ERROR: "error",
        AppStatus.STOPPED: "",
    }

    def __init__(self, theme: str = "light", icon_dir: str = "shells/tray/icons") -> None:
        self._theme = theme
        self._icon_dir = icon_dir

    def resolve(self, status: AppStatus) -> str:
        name = self._NAMES[status]
        if not name:
            return ""
        return f"{self._icon_dir}/{self._theme}/{name}.png"
