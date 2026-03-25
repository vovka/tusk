import configparser
import glob
import os
import re
from dataclasses import asdict, dataclass

__all__ = ["AppCatalog"]

_PLACEHOLDER = re.compile(r"\s*%\w")


_DEFAULT_DIRS = ["/usr/share/applications", "/usr/local/share/applications", "/home-apps", "/snap-apps"]


@dataclass(frozen=True)
class AppEntry:
    name: str
    exec_cmd: str


class AppCatalog:
    def __init__(self, desktop_dirs: list[str] = _DEFAULT_DIRS) -> None:
        self._dirs = desktop_dirs

    def list_apps(self) -> list[AppEntry]:
        paths = [p for d in self._dirs for p in glob.glob(f"{d}/*.desktop")]
        entries = [self._parse(p) for p in paths]
        return sorted([e for e in entries if e], key=lambda e: e.name)

    def list_dicts(self) -> list[dict]:
        return [asdict(item) for item in self.list_apps()]

    def search(self, query: str, limit: int = 10) -> list[AppEntry]:
        ranked = [_ranked(item, query.casefold()) for item in self.list_apps()]
        matches = [item for item in ranked if item]
        return [app for _, app in sorted(matches, key=lambda item: item[0])[:limit]]

    def _parse(self, path: str) -> AppEntry | None:
        config = self._read_config(path)
        if not config.has_section("Desktop Entry"):
            return None
        section = config["Desktop Entry"]
        if section.get("nodisplay", "false").lower() == "true":
            return None
        if section.get("type", "") != "Application":
            return None
        name = section.get("name", "")
        exec_str = section.get("exec", "")
        if not name or not exec_str:
            return None
        return AppEntry(name=name, exec_cmd=self._clean_exec(exec_str))

    def _read_config(self, path: str) -> configparser.RawConfigParser:
        config = configparser.RawConfigParser(strict=False)
        config.read(path, encoding="utf-8")
        return config

    def _clean_exec(self, exec_str: str) -> str:
        cleaned = _PLACEHOLDER.sub("", exec_str).strip()
        return cleaned.split()[0] if cleaned else ""


def _ranked(app: AppEntry, query: str) -> tuple[tuple[int, str, str], AppEntry] | None:
    name = app.name.casefold()
    command = os.path.basename(app.exec_cmd).casefold()
    score = _score(name, command, query)
    return ((score, name, command), app) if score is not None else None


def _score(name: str, command: str, query: str) -> int | None:
    if name == query:
        return 0
    if command == query:
        return 1
    if name.startswith(query):
        return 2
    if command.startswith(query):
        return 3
    if query in name:
        return 4
    return 5 if query in command else None
