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
_CURSOR_UP = "\033[A"


class ColorLogPrinter(LogPrinter):
    def __init__(self) -> None:
        self._last_line: str = ""
        self._wait_text: str = ""

    def log(self, tag: str, message: str) -> None:
        self.clear_wait()
        color = _TAG_COLORS.get(tag, _RESET)
        self._last_line = f"{color}[{tag}] {message}{_RESET}"
        print(self._last_line)

    def show_wait(self, label: str) -> None:
        self._wait_text = f" waiting for {label}..."
        suffix = f"{_DIM}{self._wait_text}{_RESET}"
        print(f"{_CURSOR_UP}\r{self._last_line}{suffix}")

    def clear_wait(self) -> None:
        if not self._wait_text:
            return
        padding = " " * len(self._wait_text)
        print(f"{_CURSOR_UP}\r{self._last_line}{padding}")
        self._wait_text = ""
