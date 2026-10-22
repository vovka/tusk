import types

import pytest

from tusk.kernel.modes.editor.editor_driver import EditorDriver
from tusk.shared.schemas.buffer_selection import BufferSelection
from tusk.shared.schemas.tools.tool_result import ToolResult


def test_goto_line_uses_ctrl_g_then_types_number() -> None:
    calls = _run(lambda driver: driver.goto_line(7))
    assert calls == [("press_keys", {"keys": "<ctrl>g"}), ("type_text", {"text": "7"}), ("press_keys", {"keys": "Return"})]


def test_paste_writes_clipboard_and_restores_it() -> None:
    calls = _run(lambda driver: driver.paste("code"))
    assert calls[0] == ("read_clipboard", {})
    assert calls[1:3] == [("write_clipboard", {"text": "code"}), ("press_keys", {"keys": "<ctrl>v"})]
    assert calls[-1] == ("write_clipboard", {"text": "held"})


def test_paste_settles_before_restoring_clipboard() -> None:
    calls: list[tuple] = []
    driver = EditorDriver(_registry(calls), "gnome", sleep=lambda seconds: calls.append(("sleep", seconds)))
    driver.paste("code")
    paste_idx = calls.index(("press_keys", {"keys": "<ctrl>v"}))
    sleep_idx = next(index for index, call in enumerate(calls) if call[0] == "sleep")
    assert paste_idx < sleep_idx < len(calls) - 1
    assert calls[-1] == ("write_clipboard", {"text": "held"})


def test_read_buffer_select_all_copy_then_restores_clipboard() -> None:
    calls = _run(lambda driver: driver.read_buffer())
    assert ("press_keys", {"keys": "<ctrl>a"}) in calls
    assert ("press_keys", {"keys": "<ctrl>c"}) in calls
    assert calls[-1] == ("write_clipboard", {"text": "held"})


def test_read_buffer_settles_after_copy_before_reading_clipboard() -> None:
    calls: list[tuple] = []
    driver = EditorDriver(_registry(calls), "gnome", sleep=lambda seconds: calls.append(("sleep", seconds)))
    driver.read_buffer()
    copy_idx = calls.index(("press_keys", {"keys": "<ctrl>c"}))
    sleep_idx = next(index for index, call in enumerate(calls) if call[0] == "sleep")
    read_idx = next(index for index, call in enumerate(calls) if call[0] == "read_clipboard" and index > copy_idx)
    assert copy_idx < sleep_idx < read_idx


def test_driver_raises_when_a_gnome_tool_fails() -> None:
    registry = types.SimpleNamespace(get=lambda name: types.SimpleNamespace(execute=lambda args: ToolResult(False, "xdotool missing", None)))
    driver = EditorDriver(registry, "gnome", sleep=lambda seconds: None)
    with pytest.raises(RuntimeError):
        driver.press_keys("<ctrl>a")


def test_select_range_spans_rows_with_shift() -> None:
    calls = _run(lambda driver: driver.select_range(BufferSelection(2, 4)))
    shift_downs = [call for call in calls if call == ("press_keys", {"keys": "<shift>Down"})]
    assert len(shift_downs) == 2
    assert calls[-1] == ("press_keys", {"keys": "<shift>End"})


def _run(action: object) -> list[tuple]:
    calls: list[tuple] = []
    driver = EditorDriver(_registry(calls), "gnome")
    action(driver)
    return calls


def _registry(calls: list[tuple]) -> object:
    def get(name: str) -> object:
        suffix = name.split(".", 1)[1]
        return types.SimpleNamespace(execute=lambda args: _record(calls, suffix, args))

    return types.SimpleNamespace(get=get)


def _record(calls: list[tuple], suffix: str, args: dict) -> ToolResult:
    calls.append((suffix, args))
    return ToolResult(True, "", {"text": "held"})


def _clipboard_registry(clipboard: dict, copy_writes: str | None, read_ok: bool) -> object:
    def execute(suffix: str, args: dict) -> ToolResult:
        if suffix == "write_clipboard":
            clipboard["text"] = args["text"]
        if suffix == "press_keys" and args["keys"] == "<ctrl>c" and copy_writes is not None:
            clipboard["text"] = copy_writes
        text = clipboard["text"]
        return ToolResult(read_ok and bool(text) if suffix == "read_clipboard" else True, "", {"text": text})

    return types.SimpleNamespace(get=lambda name: types.SimpleNamespace(execute=lambda args: execute(name.split(".", 1)[1], args)))


def test_read_buffer_returns_empty_when_clipboard_read_reports_empty() -> None:
    clipboard = {"text": "OLD"}
    driver = EditorDriver(_clipboard_registry(clipboard, "", True), "gnome", sleep=lambda seconds: None)
    assert driver.read_buffer() == ""
    assert clipboard["text"] == "OLD"


def test_read_buffer_ignores_stale_clipboard_when_copy_is_noop() -> None:
    clipboard = {"text": "OLD"}
    driver = EditorDriver(_clipboard_registry(clipboard, None, True), "gnome", sleep=lambda seconds: None)
    assert driver.read_buffer() == ""
    assert clipboard["text"] == "OLD"


def test_read_buffer_returns_copied_text() -> None:
    driver = EditorDriver(_clipboard_registry({"text": "OLD"}, "x = 1", True), "gnome", sleep=lambda s: None)
    assert driver.read_buffer() == "x = 1"
