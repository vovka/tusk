from datetime import datetime

from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.logging.log_tag_palette import color_for, content_style_for, group_names, is_always_visible, label_for

__all__ = ["ColorLogPrinter"]

_RESET = "\033[0m"


class ColorLogPrinter(LogPrinter):
    def __init__(self, enabled_groups: frozenset[str] = frozenset(), hidden_groups: frozenset[str] = frozenset()) -> None:
        self._enabled_groups = enabled_groups
        self._hidden_groups = hidden_groups

    def log(self, tag: str, message: str, group: str | None = None) -> None:
        if not self._should_print(tag, group):
            return
        lines = message.splitlines() or [""]
        for index, line in enumerate(lines):
            print(f"{self._prefix(tag)} {content_style_for(tag)}{line}{_RESET}", flush=True)

    def show_wait(self, label: str, group: str = "wait") -> None:
        if not self._should_print("LLMWAIT", group):
            return
        print(f"{self._prefix('LLMWAIT')} {content_style_for('LLMWAIT')}waiting for {label}...{_RESET}", flush=True)

    def clear_wait(self) -> None:
        pass

    def _should_print(self, tag: str, group: str | None) -> bool:
        if tag != "ERROR" and self._hidden(tag, group):
            return False
        if is_always_visible(tag):
            return True
        if not self._enabled_groups:
            return False
        return bool(group_names(tag, group).intersection(self._enabled_groups))

    def _hidden(self, tag: str, group: str | None) -> bool:
        return bool(group_names(tag, group).intersection(self._hidden_groups))

    def _prefix(self, tag: str) -> str:
        color = color_for(tag)
        ts = datetime.now().strftime("%H:%M:%S")
        return f"\033[2m{ts}\033[0m {color}[{label_for(tag)}]\033[0m"
