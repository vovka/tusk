from adapters.gnome.wayland.shell_bus import ShellBus

__all__ = ["WaylandTextPaster"]


class WaylandTextPaster:
    """Types and replaces dictated text through the tusk-shell extension."""

    def __init__(self, bus: ShellBus) -> None:
        self._bus = bus

    def paste(self, text: str) -> None:
        self._bus.call("TypeText", [text])

    def replace(self, char_count: int, new_text: str) -> None:
        # The extension types "\b" as BackSpace, so deletion and text go in one call.
        self.paste("\b" * max(char_count, 0) + new_text)
