__all__ = ["CLIShell"]


class CLIShell:
    def start(self, submit: object) -> None:
        while True:
            text = input("tusk> ")
            if text.strip().lower() in {"exit", "quit"}:
                return
            result = submit(text)
            if result.reply:
                print(result.reply)

    def stop(self) -> None:
        return None
