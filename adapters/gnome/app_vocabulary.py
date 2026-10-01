import os

from adapters.gnome.app_catalog import AppCatalog

__all__ = ["AppVocabulary"]


class AppVocabulary:
    """Installed application names as an STT prompt, so the engine spells them correctly."""

    def __init__(self, app_catalog: AppCatalog) -> None:
        self._apps = app_catalog

    @classmethod
    def installed(cls) -> "AppVocabulary":
        return cls(AppCatalog())

    def text(self) -> str:
        names = [os.path.basename(app.exec_cmd) for app in self._apps.list_apps()]
        return ", ".join(["TUSK", *names])
