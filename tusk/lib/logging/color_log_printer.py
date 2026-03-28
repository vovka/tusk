from datetime import datetime

from tusk.lib.logging.interfaces.log_printer import LogPrinter

__all__ = ["ColorLogPrinter"]

_RESET = "\033[0m"

_TAG_COLORS: dict[str, str] = {
    "USER": "\033[90m",
    "VAD": "\033[33m",
    "STT": "\033[32m",
    "GATE": "\033[36m",
    "LLM": "\033[34m",
    "LLMPAYLOAD": "\033[94m",
    "AGENT": "\033[97m",
    "TOOL": "\033[35m",
    "PIPELINE": "\033[37m",
    "DICTATION": "\033[96m",
    "ERROR": "\033[31m",
}
_ALWAYS_VISIBLE = frozenset({"USER", "TUSK", "ERROR"})
_GROUP_BY_TAG = {
    "VAD": "vad",
    "STT": "stt",
    "GATE": "gate",
    "LLM": "llm",
    "AGENT": "agent",
    "TOOL": "tool",
    "PIPELINE": "pipeline",
    "DICTATION": "dictation",
}


class ColorLogPrinter(LogPrinter):
    def __init__(self, enabled_groups: frozenset[str] = frozenset()) -> None:
        self._enabled_groups = enabled_groups

    def log(self, tag: str, message: str, group: str | None = None) -> None:
        if not self._should_print(tag, group):
            return
        color = _TAG_COLORS.get(tag, _RESET)
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = f"\033[2m{ts}\033[0m {color}[{tag}]\033[0m"
        lines = message.splitlines() or [""]
        for index, line in enumerate(lines):
            line_prefix = prefix if index == 0 else f"\033[2m{ts}\033[0m {color}[{tag}]\033[0m"
            print(f"{line_prefix} {line}{_RESET}", flush=True)

    def show_wait(self, label: str, group: str = "wait") -> None:
        if group not in self._enabled_groups:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"\033[37m{ts} waiting for {label}...{_RESET}", flush=True)

    def clear_wait(self) -> None:
        pass

    def _should_print(self, tag: str, group: str | None) -> bool:
        if tag in _ALWAYS_VISIBLE:
            return True
        if not self._enabled_groups:
            return False
        return (group or _GROUP_BY_TAG.get(tag, tag.casefold())) in self._enabled_groups
