import types

from tusk.kernel.modes.editor.edit_applier import EditApplier
from tusk.shared.schemas.buffer_selection import BufferSelection
from tusk.shared.schemas.edit_operation import EditOperation


def test_insert_goes_to_line_then_pastes() -> None:
    driver, calls = _driver()
    EditApplier().apply(EditOperation("insert", 3, 3, "print()"), driver)
    assert calls == [("goto_line", 3), ("paste", "print()")]


def test_replace_selects_then_pastes() -> None:
    driver, calls = _driver()
    EditApplier().apply(EditOperation("replace", 2, 4, "x"), driver)
    assert calls == [("select_range", BufferSelection(2, 4)), ("paste", "x")]


def test_delete_selects_then_presses_delete() -> None:
    driver, calls = _driver()
    EditApplier().apply(EditOperation("delete", 5, 6, ""), driver)
    assert calls == [("select_range", BufferSelection(5, 6)), ("press_keys", "Delete")]


def test_matching_buffer_skips_full_replace() -> None:
    driver, calls = _driver(buffer_text="expected")
    EditApplier().apply(EditOperation("insert", 1, 1, "x", "expected"), driver)
    assert calls == [("goto_line", 1), ("paste", "x"), ("read_buffer", None)]


def test_drifted_buffer_repaints_whole_buffer() -> None:
    driver, calls = _driver(buffer_text="drifted")
    EditApplier().apply(EditOperation("insert", 1, 1, "x", "expected"), driver)
    assert calls == [("goto_line", 1), ("paste", "x"), ("read_buffer", None), ("replace_buffer", "expected")]


def test_empty_full_buffer_skips_verification() -> None:
    driver, calls = _driver(buffer_text=None)
    EditApplier().apply(EditOperation("insert", 1, 1, "x", ""), driver)
    assert calls == [("goto_line", 1), ("paste", "x")]


def _driver(buffer_text: str | None = "") -> tuple[object, list[tuple]]:
    calls: list[tuple] = []
    names = ["goto_line", "select_range", "paste", "press_keys", "replace_buffer", "type_text"]
    recorders = {name: (lambda arg, name=name: calls.append((name, arg))) for name in names}
    return types.SimpleNamespace(read_buffer=lambda: _read(calls, buffer_text), **recorders), calls


def _read(calls: list[tuple], buffer_text: str | None) -> str:
    if buffer_text is None:
        raise AssertionError("read_buffer must not be called without a full_buffer")
    calls.append(("read_buffer", None))
    return buffer_text
