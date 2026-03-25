from tusk.kernel.interfaces.shell import Shell

__all__ = ["CLIShell"]


class CLIShell(Shell):
    def start(self, api: object) -> None:
        while True:
            text = input("tusk> ")
            if text.strip().lower() in {"exit", "quit"}:
                return
            result = api.submit_text(text)
            if result.reply:
                print(result.reply)

    def stop(self) -> None:
        return None
