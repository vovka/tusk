from datetime import datetime

from tusk.interfaces.log_printer import LogPrinter

__all__ = ["ColorLogPrinter"]

_RESET = "\033[0m"

_TAG_COLORS: dict[str, str] = {
    "VAD": "\033[33m",
    "STT": "\033[32m",
    "GATE": "\033[36m",
    "LLM": "\033[34m",
    "AGENT": "\033[97m",
    "TOOL": "\033[35m",
    "PIPELINE": "\033[37m",
    "DICTATION": "\033[96m",
    "ERROR": "\033[31m",
}


class ColorLogPrinter(LogPrinter):
    def log(self, tag: str, message: str) -> None:
        color = _TAG_COLORS.get(tag, _RESET)
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"\033[2m{ts}\033[0m {color}[{tag}] {message}{_RESET}", flush=True)

    def show_wait(self, label: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"\033[37m{ts} waiting for {label}...{_RESET}", flush=True)

    def clear_wait(self) -> None:
        pass
