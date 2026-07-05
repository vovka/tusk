__all__ = ["ClipboardGuard"]


class ClipboardGuard:
    def __init__(self, tool_registry: object, desktop_source: str) -> None:
        self._registry = tool_registry
        self._source = desktop_source
        self._saved = ""

    def __enter__(self) -> "ClipboardGuard":
        self._saved = self._read()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        self._registry.get(f"{self._source}.write_clipboard").execute({"text": self._saved})
        return False

    def _read(self) -> str:
        result = self._registry.get(f"{self._source}.read_clipboard").execute({})
        return (result.data or {}).get("text", "")
