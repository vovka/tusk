from adapters.gnome.gnome_input_simulator import GnomeInputSimulator
from adapters.gnome.wayland.shell_bus import ShellBus

__all__ = ["WaylandInputSimulator"]


class WaylandInputSimulator(GnomeInputSimulator):
    """Sends keyboard and pointer input through the tusk-shell extension's virtual devices."""

    def __init__(self, bus: ShellBus) -> None:
        self._bus = bus

    def press_keys(self, keys: str) -> None:
        self._bus.call("KeyCombo", [self._normalize_keys(keys).split("+")])

    def _type_segment(self, text: str) -> None:
        self._bus.call("TypeText", [text])

    def replace_text(self, char_count: int, text: str) -> None:
        # The extension types "\b" as BackSpace, so deletion and text go in one call.
        self._bus.call("TypeText", ["\b" * max(char_count, 0) + text])

    def mouse_click(self, x: int, y: int, button: int, clicks: int) -> None:
        self.mouse_move(x, y)
        for _ in range(clicks):
            self._bus.call("PointerButton", [button, True])
            self._bus.call("PointerButton", [button, False])

    def mouse_move(self, x: int, y: int) -> None:
        self._bus.call("PointerMove", [x, y])

    def mouse_drag(self, from_x: int, from_y: int, to_x: int, to_y: int, button: int) -> None:
        self.mouse_move(from_x, from_y)
        self._bus.call("PointerButton", [button, True])
        self.mouse_move(to_x, to_y)
        self._bus.call("PointerButton", [button, False])

    def mouse_scroll(self, direction: str, clicks: int) -> None:
        self._bus.call("Scroll", [direction != "up", clicks])
