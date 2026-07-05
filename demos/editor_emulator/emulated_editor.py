__all__ = ["EmulatedEditor"]


class EmulatedEditor:
    """In-memory stand-in for a focused text editor driven via keystrokes and clipboard."""

    def __init__(self) -> None:
        self._buffer = ""
        self._clipboard = ""
        self._select_all_active = False

    @property
    def buffer(self) -> str:
        return self._buffer

    @property
    def clipboard(self) -> str:
        return self._clipboard

    def press_keys(self, keys: str) -> None:
        if keys == "<ctrl>a":
            self._select_all_active = True
        elif keys == "<ctrl>c":
            self._copy()
        elif keys == "<ctrl>v":
            self._paste()
        else:
            self._select_all_active = False

    def type_text(self, text: str) -> None:
        self._insert(text)

    def write_clipboard(self, text: str) -> None:
        self._clipboard = text

    def _copy(self) -> None:
        if self._select_all_active:
            self._clipboard = self._buffer

    def _paste(self) -> None:
        self._insert(self._clipboard)

    def _insert(self, text: str) -> None:
        self._buffer = text if self._select_all_active else self._buffer + text
        self._select_all_active = False
