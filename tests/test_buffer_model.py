from adapters.coding.buffer_model import BufferModel


def test_from_text_and_to_text_round_trip() -> None:
    model = BufferModel.from_text("a\nb\nc")
    assert model.lines == ("a", "b", "c")
    assert model.to_text() == "a\nb\nc"


def test_with_edit_replace_swaps_target_range() -> None:
    model = BufferModel.from_text("a\nb\nc")
    edited = model.with_edit({"kind": "replace", "target_start": 2, "target_end": 2, "new_text": "B"})
    assert edited.to_text() == "a\nB\nc"


def test_with_edit_insert_adds_lines_before_target() -> None:
    model = BufferModel.from_text("a\nc")
    edited = model.with_edit({"kind": "insert", "target_start": 2, "target_end": 2, "new_text": "b"})
    assert edited.to_text() == "a\nb\nc"


def test_with_edit_delete_removes_target_range() -> None:
    model = BufferModel.from_text("a\nb\nc")
    edited = model.with_edit({"kind": "delete", "target_start": 2, "target_end": 2})
    assert edited.to_text() == "a\nc"


def test_with_edit_returns_new_instance() -> None:
    model = BufferModel.from_text("a")
    edited = model.with_edit({"kind": "insert", "target_start": 1, "target_end": 1, "new_text": "x"})
    assert model.to_text() == "a"
    assert edited.to_text() == "x\na"
