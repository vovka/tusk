from adapters.gnome.gnome_clipboard_tools import GnomeClipboardTools


def test_write_clipboard_returns_written_text() -> None:
    clipboard = _clipboard()
    result = GnomeClipboardTools(clipboard).write_clipboard({"text": "frozen text"})
    assert result["message"] == "clipboard written"
    assert result["data"] == {"clipboard_text": "frozen text"}
    assert clipboard.writes == ["frozen text"]


def _clipboard() -> object:
    class Clipboard:
        def __init__(self) -> None:
            self.writes: list[str] = []

        def write(self, text: str) -> None:
            self.writes.append(text)

    return Clipboard()
