from tusk.kernel.modes.full_replace_edit_strategy import FullReplaceEditStrategy
from tusk.kernel.modes.line_anchored_edit_strategy import LineAnchoredEditStrategy
from tusk.shared.schemas.buffer_selection import BufferSelection
from tusk.shared.schemas.edit_operation import EditOperation


def test_line_anchored_insert_goes_to_line_then_pastes() -> None:
    driver, calls = _driver()
    LineAnchoredEditStrategy().apply(EditOperation("insert", 3, 3, "print()"), driver)
    assert calls == [("goto_line", 3), ("paste", "print()")]


def test_line_anchored_replace_selects_then_pastes() -> None:
    driver, calls = _driver()
    LineAnchoredEditStrategy().apply(EditOperation("replace", 2, 4, "x"), driver)
    assert calls == [("select_range", BufferSelection(2, 4)), ("paste", "x")]


def test_line_anchored_delete_selects_then_presses_delete() -> None:
    driver, calls = _driver()
    LineAnchoredEditStrategy().apply(EditOperation("delete", 5, 6, ""), driver)
    assert calls == [("select_range", BufferSelection(5, 6)), ("press_keys", "Delete")]


def test_full_replace_repaints_whole_buffer() -> None:
    driver, calls = _driver()
    FullReplaceEditStrategy().apply(EditOperation("replace", 1, 1, "x", "whole\nbuffer"), driver)
    assert calls == [("replace_buffer", "whole\nbuffer")]


def _driver() -> tuple[object, list[tuple]]:
    calls: list[tuple] = []
    return _record_driver(calls), calls


def _record_driver(calls: list[tuple]) -> object:
    import types

    def record(name: str):
        return lambda arg: calls.append((name, arg))

    names = ["goto_line", "select_range", "paste", "press_keys", "replace_buffer", "type_text"]
    return types.SimpleNamespace(**{name: record(name) for name in names})
