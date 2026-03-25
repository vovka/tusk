import types

from adapters.gnome.gnome_input_tools import GnomeInputTools


def test_type_text_rejects_control_characters() -> None:
    tools = GnomeInputTools(_input(), _paster(), _chunker())
    result = tools.type_text({"text": "\u0001\u007f"})
    assert result["success"] is False
    assert "use press_keys" in result["message"]


def test_press_keys_reports_input_failure() -> None:
    failing = types.SimpleNamespace(press_keys=lambda keys: (_ for _ in ()).throw(RuntimeError("bad shortcut")))
    tools = GnomeInputTools(failing, _paster(), _chunker())
    result = tools.press_keys({"keys": "<Ctrl>c"})
    assert result["success"] is False
    assert result["message"] == "bad shortcut"


def test_type_text_splits_large_text_into_chunks() -> None:
    calls: list[str] = []
    input_simulator = types.SimpleNamespace(type_text=lambda text: calls.append(text))
    tools = GnomeInputTools(input_simulator, _paster(), types.SimpleNamespace(split=lambda text: ["ab", "cd"]))
    result = tools.type_text({"text": "abcd"})
    assert result["success"] is True
    assert calls == ["ab", "cd"]


def _input() -> object:
    return types.SimpleNamespace(type_text=lambda text: (_ for _ in ()).throw(AssertionError("should not be called")))


def _paster() -> object:
    return types.SimpleNamespace(replace=lambda count, text: (_ for _ in ()).throw(AssertionError("unused")))


def _chunker() -> object:
    return types.SimpleNamespace(split=lambda text: [text])
