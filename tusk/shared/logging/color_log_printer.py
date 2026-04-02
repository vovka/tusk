from datetime import datetime

from tusk.shared.logging.interfaces.log_printer import LogPrinter

__all__ = ["ColorLogPrinter"]

_RESET = "\033[0m"

_TAG_COLORS: dict[str, str] = {
    "USER": "\033[90m",
    "READY": "\033[92m",
    "DETECTOR": "\033[33m",
    "TRANSCRIBER": "\033[32m",
    "SANITIZER": "\033[96m",
    "BUFFER": "\033[95m",
    "GATEKEEPER": "\033[36m",
    "KERNELINPUT": "\033[37m",
    "LLMREQUEST": "\033[34m",
    "LLMPAYLOAD": "\033[94m",
    "LLMWAIT": "\033[37m",
    "AGENT": "\033[97m",
    "TOOL": "\033[35m",
    "PIPELINE": "\033[37m",
    "DICTATION": "\033[96m",
    "ERROR": "\033[31m",
}
_ALWAYS_VISIBLE = frozenset({"USER", "TUSK", "ERROR", "READY"})
_GROUP_BY_TAG = {
    "READY": "ready",
    "DETECTOR": "detector",
    "TRANSCRIBER": "transcriber",
    "SANITIZER": "sanitizer",
    "BUFFER": "buffer",
    "GATEKEEPER": "gatekeeper",
    "KERNELINPUT": "kernel-input",
    "LLMREQUEST": "llm-request",
    "LLMPAYLOAD": "llm-payload",
    "LLMWAIT": "llm-wait",
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
        lines = message.splitlines() or [""]
        for index, line in enumerate(lines):
            print(f"{self._prefix(tag)} {line}{_RESET}", flush=True)

    def show_wait(self, label: str, group: str = "wait") -> None:
        if not self._should_print("LLMWAIT", group):
            return
        print(f"{self._prefix('LLMWAIT')} waiting for {label}...{_RESET}", flush=True)

    def clear_wait(self) -> None:
        pass

    def _should_print(self, tag: str, group: str | None) -> bool:
        if tag in _ALWAYS_VISIBLE:
            return True
        if not self._enabled_groups:
            return False
        return (group or _GROUP_BY_TAG.get(tag, tag.casefold())) in self._enabled_groups

    def _prefix(self, tag: str) -> str:
        color = _TAG_COLORS.get(tag, _RESET)
        ts = datetime.now().strftime("%H:%M:%S")
        return f"\033[2m{ts}\033[0m {color}[{tag}]\033[0m"
