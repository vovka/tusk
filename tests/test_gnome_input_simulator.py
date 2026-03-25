import types
from unittest.mock import patch

from adapters.gnome.gnome_input_simulator import GnomeInputSimulator


def test_press_keys_normalizes_angle_bracket_shortcuts() -> None:
    command: list[str] = []
    with patch("adapters.gnome.gnome_input_simulator.subprocess.run", side_effect=_capture(command)):
        GnomeInputSimulator().press_keys("<Ctrl>c")
    assert command[-1] == "ctrl+c"


def _capture(command: list[str]) -> object:
    def run(args: list[str], check: bool = False) -> object:
        command[:] = args
        return types.SimpleNamespace(returncode=0)

    return run
