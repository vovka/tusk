from datetime import datetime

from tusk.interfaces.log_printer import LogPrinter

__all__ = ["ColorLogPrinter"]

_RESET = "\033[0m"

_TAG_COLORS: dict[str, str] = {
    "VAD": "\033[33m",
    "STT": "\033[32m",
    "GATE": "\033[36m",
    "LLM": "\033[34m",
    "AGENT": "\033[90m",
    "TOOL": "\033[35m",
    "PIPELINE": "\033[37m",
    "DICTATION": "\033[96m",
    "ERROR": "\033[31m",
}

_DIM = "\033[2m"
_ERASE_TO_END = "\033[K"


class ColorLogPrinter(LogPrinter):
    def __init__(self) -> None:
        self._wait_len: int = 0
        self._has_content: bool = False

    def log(self, tag: str, message: str) -> None:
        self._finish_line()
        color = _TAG_COLORS.get(tag, _RESET)
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"{_DIM}{ts}{_RESET} {color}[{tag}] {message}{_RESET}"
        print(line, end="", flush=True)
        self._has_content = True

    def show_wait(self, label: str) -> None:
        self.clear_wait()
        wait = f" waiting for {label}..."
        self._wait_len = len(wait)
        print(f"{_DIM}{wait}{_RESET}", end="", flush=True)

    def clear_wait(self) -> None:
        if self._wait_len == 0:
            return
        print("\b" * self._wait_len + _ERASE_TO_END, end="", flush=True)
        self._wait_len = 0

    def _finish_line(self) -> None:
        self.clear_wait()
        if self._has_content:
            print(flush=True)
            self._has_content = False
