import types
from unittest.mock import patch

from adapters.gnome.gnome_input_simulator import GnomeInputSimulator


def test_press_keys_normalizes_angle_bracket_shortcuts() -> None:
    command: list[str] = []
    with patch("adapters.gnome.gnome_input_simulator.subprocess.run", side_effect=_capture(command)):
        GnomeInputSimulator().press_keys("<Ctrl>c")
    assert command[-1] == "ctrl+c"


def test_type_text_raises_on_failure() -> None:
    result = types.SimpleNamespace(returncode=1, stderr="XGetInputFocus returned the focused window of 1")
    with patch("adapters.gnome.gnome_input_simulator.subprocess.run", return_value=result):
        try:
            GnomeInputSimulator().type_text("hello")
        except RuntimeError as exc:
            assert "failed to type text" in str(exc)
            assert "exit=1" in str(exc)
            assert "XGetInputFocus" in str(exc)
        else:
            raise AssertionError("expected RuntimeError")


def _capture(command: list[str]) -> object:
    def run(args: list[str], check: bool = False, capture_output: bool = False, text: bool = False) -> object:
        command[:] = args
        return types.SimpleNamespace(returncode=0, stderr="")

    return run
