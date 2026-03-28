__all__ = ["GnomeClipboardTools"]


class GnomeClipboardTools:
    def __init__(self, clipboard_provider: object) -> None:
        self._clipboard = clipboard_provider

    def read_clipboard(self, arguments: dict) -> dict:
        text = self._clipboard.read()
        return {"success": bool(text), "message": text or "clipboard empty", "data": {"text": text}}

    def write_clipboard(self, arguments: dict) -> dict:
        self._clipboard.write(arguments["text"])
        return {"success": True, "message": "clipboard written"}
