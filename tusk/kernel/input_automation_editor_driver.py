import time
from collections.abc import Callable

from tusk.kernel.clipboard_guard import ClipboardGuard
from tusk.kernel.interfaces.editor_driver import EditorDriver
from tusk.shared.schemas.buffer_selection import BufferSelection
from tusk.kernel.tool_registry import ToolRegistry

__all__ = ["InputAutomationEditorDriver"]

# xdotool returns before the target app consumes a copy/paste keystroke, so the
# clipboard must settle before we read or restore it, or we lose the round-trip.
_CLIPBOARD_SETTLE_SECONDS = 0.2


class InputAutomationEditorDriver(EditorDriver):
    def __init__(self, tool_registry: ToolRegistry, desktop_source: str, sleep: Callable[[float], None] = time.sleep) -> None:
        self._registry = tool_registry
        self._source = desktop_source
        self._sleep = sleep

    def read_buffer(self) -> str:
        with ClipboardGuard(self._registry, self._source):
            self._press("<ctrl>a")
            self._press("<ctrl>c")
            self._sleep(_CLIPBOARD_SETTLE_SECONDS)
            return self._read_clipboard()

    def goto_line(self, line_number: int) -> None:
        self._press("<ctrl>g")
        self._exec("type_text", {"text": str(line_number)})
        self._press("Return")

    def select_range(self, selection: BufferSelection) -> None:
        self.goto_line(selection.start_line)
        self._press("Home")
        self._span(selection)

    def paste(self, text: str) -> None:
        with ClipboardGuard(self._registry, self._source):
            self._exec("write_clipboard", {"text": text})
            self._press("<ctrl>v")
            self._sleep(_CLIPBOARD_SETTLE_SECONDS)

    def type_text(self, text: str) -> None:
        self._exec("type_text", {"text": text})

    def press_keys(self, keys: str) -> None:
        self._press(keys)

    def replace_buffer(self, text: str) -> None:
        self._press("<ctrl>a")
        self.paste(text)

    def _span(self, selection: BufferSelection) -> None:
        for _ in range(selection.end_line - selection.start_line):
            self._press("<shift>Down")
        self._press("<shift>End")

    def _read_clipboard(self) -> str:
        return (self._exec("read_clipboard", {}).data or {}).get("text", "")

    def _press(self, keys: str) -> None:
        self._exec("press_keys", {"keys": keys})

    def _exec(self, name: str, arguments: dict) -> object:
        result = self._registry.get(f"{self._source}.{name}").execute(arguments)
        if not result.success:
            raise RuntimeError(f"{self._source}.{name} failed: {result.message}")
        return result
