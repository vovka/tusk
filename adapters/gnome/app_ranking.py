import os
import subprocess

from tusk.shared.schemas.desktop.app_entry import AppEntry

__all__ = ["DEFAULT_CATEGORIES", "ranked", "system_default_app"]

_CATEGORY_WORDS = {
    "browser": "WebBrowser",
    "web browser": "WebBrowser",
    "terminal": "TerminalEmulator",
    "file manager": "FileManager",
    "text editor": "TextEditor",
    "calculator": "Calculator",
}
_DEFAULT_COMMANDS = {
    "TextEditor": ["xdg-mime", "query", "default", "text/plain"],
    "WebBrowser": ["xdg-settings", "get", "default-web-browser"],
    "FileManager": ["xdg-mime", "query", "default", "inode/directory"],
}
DEFAULT_CATEGORIES = tuple(_DEFAULT_COMMANDS)


def system_default_app(category: str) -> str | None:
    try:
        result = subprocess.run(_DEFAULT_COMMANDS[category], capture_output=True, text=True, timeout=2, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None


def ranked(app: AppEntry, query: str) -> tuple[tuple[int, str, str], AppEntry] | None:
    name = app.name.casefold()
    command = os.path.basename(app.exec_cmd).casefold()
    score = _score(app, name, command, query)
    return ((score, name, command), app) if score is not None else None


def _score(app: AppEntry, name: str, command: str, query: str) -> int | None:
    for score, match in enumerate(_matches(app, name, command, query)):
        if match:
            return score
    return None


def _matches(app: AppEntry, name: str, command: str, query: str) -> tuple[bool, ...]:
    return (
        name == query,
        command == query,
        app.generic_name.casefold() == query,
        _has_tag(app, query),
        name.startswith(query),
        command.startswith(query),
        query in name,
        query in command,
    )


def _has_tag(app: AppEntry, query: str) -> bool:
    keywords = {keyword.casefold() for keyword in app.keywords}
    return query in keywords or _CATEGORY_WORDS.get(query) in app.categories
