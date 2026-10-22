from collections.abc import Callable

from tusk.shared.interfaces.shell import Shell
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["CLIShell"]


class CLIShell(Shell):
    def start(self, submit: Callable[[str], KernelResponse]) -> None:
        while True:
            text = input("tusk> ")
            if text.strip().lower() in {"exit", "quit"}:
                return
            result = submit(text)
            if result.reply:
                print(result.reply)
