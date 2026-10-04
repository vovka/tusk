from adapters.gnome.app_catalog import AppCatalog
from tusk.shared.schemas.desktop.app_entry import AppEntry

__all__ = ["AppVocabulary"]

# Whisper echoes a long prompt back on silence, so keep it short and free of settings-panel noise.
_MAX_NAMES = 25
_WAKE_WORD = "TUSK"
_SETTINGS_CATEGORIES = {"Settings", "DesktopSettings", "X-XFCE-SettingsDialog"}
_SETTINGS_WORDS = ("settings", "preferences")


class AppVocabulary:
    """Wake word plus user-facing application names as an STT prompt, so the engine spells them correctly."""

    def __init__(self, app_catalog: AppCatalog) -> None:
        self._apps = app_catalog

    @classmethod
    def installed(cls) -> "AppVocabulary":
        return cls(AppCatalog())

    def stt_prompt(self, enabled: bool) -> str:
        return self.text() if enabled else _WAKE_WORD

    def text(self) -> str:
        names: dict[str, str] = {}
        for app in sorted(self._apps.list_apps(), key=lambda item: item.name.casefold()):
            if not _is_settings_panel(app):
                names.setdefault(app.name.casefold(), app.name)
        return ", ".join([_WAKE_WORD, *list(names.values())[:_MAX_NAMES]])


def _is_settings_panel(app: AppEntry) -> bool:
    return bool(_SETTINGS_CATEGORIES & set(app.categories)) or any(word in app.name.casefold() for word in _SETTINGS_WORDS)
