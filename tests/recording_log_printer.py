class RecordingLogPrinter:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, str | None]] = []

    def log(self, tag: str, message: str, group: str | None = None) -> None:
        self.messages.append((tag, message, group))

    def show_wait(self, label: str, group: str = "wait") -> None:
        pass

    def clear_wait(self) -> None:
        pass
