import configparser
import glob
import os
import re
from collections.abc import Callable

from adapters.gnome.app_ranking import DEFAULT_CATEGORIES, ranked, system_default_app
from tusk.shared.desktop.fuzzy_name_matcher import FuzzyNameMatcher
from tusk.shared.schemas.desktop.app_entry import AppEntry

__all__ = ["AppCatalog"]

_PLACEHOLDER = re.compile(r"\s*%\w")


_GENERIC_TIERS = (2, 3)
_DEFAULT_DIRS = ["/usr/share/applications", "/usr/local/share/applications", "/home-apps", "/snap-apps"]


class AppCatalog:
    def __init__(
        self,
        desktop_dirs: list[str] = _DEFAULT_DIRS,
        matcher: FuzzyNameMatcher | None = None,
        default_app: Callable[[str], str | None] | None = None,
    ) -> None:
        self._dirs = desktop_dirs
        self._matcher = matcher or FuzzyNameMatcher()
        self._default_app = default_app or system_default_app

    def list_apps(self) -> list[AppEntry]:
        paths = [p for d in self._dirs for p in glob.glob(f"{d}/*.desktop")]
        entries = [self._parse(p) for p in paths]
        return sorted([e for e in entries if e], key=lambda e: e.name)

    def search(self, query: str, limit: int = 10) -> list[AppEntry]:
        matches = [rank for rank in (ranked(item, query.casefold()) for item in self.list_apps()) if rank]
        if not matches:
            return self._fuzzy_search(query)
        defaults = self._defaults(matches)
        ordered = sorted(matches, key=lambda item: (not _is_generic_default(item, defaults), item[0]))
        return [app for _, app in ordered[:limit]]

    def suggest(self, query: str, limit: int = 5) -> list[str]:
        names = {name for app in self.list_apps() for name in (app.name, os.path.basename(app.exec_cmd)) if name}
        return self._matcher.candidates(query, sorted(names), limit)

    def _defaults(self, matches: list[tuple[tuple[int, str, str], AppEntry]]) -> set[str]:
        if min(rank[0] for rank, _ in matches) not in _GENERIC_TIERS:
            return set()
        return {self._default_app(category) for category in DEFAULT_CATEGORIES} - {None, ""}

    def _fuzzy_search(self, query: str) -> list[AppEntry]:
        by_command = {os.path.basename(app.exec_cmd).casefold(): app for app in self.list_apps()}
        closest = self._matcher.closest(query, list(by_command))
        return [by_command[closest]] if closest else []

    def _parse(self, path: str) -> AppEntry | None:
        section = self._section(self._read_config(path))
        if section is None or not section.get("name") or not section.get("exec"):
            return None
        return self._entry(section, path)

    def _entry(self, section: configparser.SectionProxy, path: str) -> AppEntry:
        return AppEntry(
            name=section["name"],
            exec_cmd=self._clean_exec(section["exec"]),
            generic_name=section.get("genericname", ""),
            keywords=_split_list(section.get("keywords", "")),
            categories=_split_list(section.get("categories", "")),
            desktop_id=os.path.basename(path),
        )

    def _read_config(self, path: str) -> configparser.RawConfigParser:
        config = configparser.RawConfigParser(strict=False)
        config.read(path, encoding="utf-8")
        return config

    def _section(self, config: configparser.RawConfigParser) -> configparser.SectionProxy | None:
        if not config.has_section("Desktop Entry"):
            return None
        section = config["Desktop Entry"]
        if any(section.get(flag, "false").lower() == "true" for flag in ("nodisplay", "hidden")):
            return None
        return section if section.get("type", "") == "Application" else None

    def _clean_exec(self, exec_str: str) -> str:
        cleaned = _PLACEHOLDER.sub("", exec_str).strip()
        return cleaned.split()[0] if cleaned else ""


def _is_generic_default(match: tuple[tuple[int, str, str], AppEntry], defaults: set[str]) -> bool:
    # A generic query ("text editor") goes to the system default even when another app matches a tighter tier.
    return match[0][0] in _GENERIC_TIERS and match[1].desktop_id in defaults


def _split_list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(";") if item.strip())
