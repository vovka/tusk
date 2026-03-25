import types

from adapters.gnome.gnome_input_tools import GnomeInputTools


def test_type_text_rejects_control_characters() -> None:
    tools = GnomeInputTools(_input(), _paster())
    result = tools.type_text({"text": "\u0001\u007f"})
    assert result["success"] is False
    assert "use press_keys" in result["message"]


def _input() -> object:
    return types.SimpleNamespace(type_text=lambda text: (_ for _ in ()).throw(AssertionError("should not be called")))


def _paster() -> object:
    return types.SimpleNamespace(replace=lambda count, text: (_ for _ in ()).throw(AssertionError("unused")))
