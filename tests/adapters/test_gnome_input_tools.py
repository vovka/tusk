import types

from adapters.gnome.tools.input_tools import InputTools


def test_type_text_rejects_control_characters() -> None:
    tools = InputTools(_input())
    result = tools.type_text({"text": "\u0001\u007f"})
    assert result["success"] is False
    assert "use press_keys" in result["message"]


def test_press_keys_reports_input_failure() -> None:
    failing = types.SimpleNamespace(press_keys=lambda keys: (_ for _ in ()).throw(RuntimeError("bad shortcut")))
    tools = InputTools(failing)
    result = tools.press_keys({"keys": "<Ctrl>c"})
    assert result["success"] is False
    assert result["message"] == "bad shortcut"


def test_type_text_splits_large_text_into_300_char_chunks() -> None:
    calls: list[str] = []
    input_simulator = types.SimpleNamespace(type_text=lambda text: calls.append(text))
    result = InputTools(input_simulator).type_text({"text": "x" * 650})
    assert result["success"] is True
    assert calls == ["x" * 300, "x" * 300, "x" * 50]


def test_type_text_reports_input_failure() -> None:
    failing = types.SimpleNamespace(type_text=lambda text: (_ for _ in ()).throw(RuntimeError("typing failed")))
    tools = InputTools(failing)
    result = tools.type_text({"text": "abcd"})
    assert result["success"] is False
    assert result["message"] == "typing failed"


def test_replace_recent_text_delegates_to_simulator() -> None:
    calls: list[tuple[int, str]] = []
    input_simulator = types.SimpleNamespace(replace_text=lambda count, text: calls.append((count, text)))
    result = InputTools(input_simulator).replace_recent_text({"replace_chars": "3", "text": "hi"})
    assert result == {"success": True, "message": "replaced"}
    assert calls == [(3, "hi")]


def _input() -> object:
    return types.SimpleNamespace(type_text=lambda text: (_ for _ in ()).throw(AssertionError("should not be called")))
