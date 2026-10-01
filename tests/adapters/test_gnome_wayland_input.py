from adapters.gnome.wayland.wayland_input_simulator import WaylandInputSimulator
from adapters.gnome.wayland.wayland_text_paster import WaylandTextPaster
from tests.adapters.wayland_fake_bus import FakeBus


def test_press_keys_sends_normalized_combo() -> None:
    bus = FakeBus()
    WaylandInputSimulator(bus).press_keys("<Ctrl>c")
    assert bus.calls == [("KeyCombo", [["ctrl", "c"]])]


def test_type_text_presses_return_for_newlines() -> None:
    bus = FakeBus()
    WaylandInputSimulator(bus).type_text("one\ntwo")
    assert bus.calls == [("TypeText", ["one"]), ("KeyCombo", [["Return"]]), ("TypeText", ["two"])]


def test_mouse_click_moves_then_presses_and_releases() -> None:
    bus = FakeBus()
    WaylandInputSimulator(bus).mouse_click(10, 20, 1, 2)
    assert bus.calls[0] == ("PointerMove", [10, 20])
    assert bus.calls[1:] == [("PointerButton", [1, True]), ("PointerButton", [1, False])] * 2


def test_mouse_scroll_sends_direction_and_clicks() -> None:
    bus = FakeBus()
    WaylandInputSimulator(bus).mouse_scroll("down", 3)
    assert bus.calls == [("Scroll", [True, 3])]


def test_text_paster_replace_types_backspaces_then_text() -> None:
    bus = FakeBus()
    WaylandTextPaster(bus).replace(2, "hi")
    assert bus.calls == [("TypeText", ["\b\bhi"])]
