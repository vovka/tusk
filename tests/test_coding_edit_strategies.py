import types

from tusk.kernel.full_replace_edit_strategy import FullReplaceEditStrategy
from tusk.shared.schemas.edit_operation import EditOperation


def test_full_replace_repaints_whole_buffer() -> None:
    calls: list[tuple] = []
    driver = types.SimpleNamespace(replace_buffer=lambda text: calls.append(("replace_buffer", text)))
    FullReplaceEditStrategy().apply(EditOperation("replace", 1, 1, "x", "whole\nbuffer"), driver)
    assert calls == [("replace_buffer", "whole\nbuffer")]
