import configparser
import glob
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
