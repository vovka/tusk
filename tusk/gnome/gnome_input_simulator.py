import subprocess

from tusk.interfaces.input_simulator import InputSimulator

__all__ = ["GnomeInputSimulator"]

_BUTTON_MAP = {"left": 1, "right": 3, "middle": 2}


class GnomeInputSimulator(InputSimulator):
    def press_keys(self, keys: str) -> None:
        subprocess.run(["xdotool", "key", "--delay", "0", keys], check=False)

    def type_text(self, text: str) -> None:
        subprocess.run(["xdotool", "type", "--delay", "0", "--", text], check=False)

    def mouse_click(self, x: int, y: int, button: int, clicks: int) -> None:
        self.mouse_move(x, y)
        subprocess.run(
            ["xdotool", "click", "--repeat", str(clicks), str(button)],
            check=False,
        )

    def mouse_move(self, x: int, y: int) -> None:
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], check=False)

    def mouse_drag(self, from_x: int, from_y: int, to_x: int, to_y: int, button: int) -> None:
        self.mouse_move(from_x, from_y)
        subprocess.run(["xdotool", "mousedown", str(button)], check=False)
        self.mouse_move(to_x, to_y)
        subprocess.run(["xdotool", "mouseup", str(button)], check=False)

    def mouse_scroll(self, direction: str, clicks: int) -> None:
        button = 4 if direction == "up" else 5
        subprocess.run(
            ["xdotool", "click", "--repeat", str(clicks), str(button)],
            check=False,
        )
