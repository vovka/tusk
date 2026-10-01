__all__ = ["TEXT", "WAYLAND_STEPS", "X11_STEPS"]

TEXT = "Hello from Tusk on Wayland\nПривіт"

# A step is a (tool, arguments) pair or a driver action: "shot:<name>", "clipboard", "save", "check_saved".
WAYLAND_STEPS = [
    ("press_keys", {"keys": "Escape"}),  # the headless shell starts in the overview
    ("launch_application", {"application_name": "gedit"}),
    ("get_active_window", {}),
    ("type_text", {"text": TEXT}), "shot:after_type",
    ("tile_window", {"window_title": "gedit", "side": "left"}), ("list_windows", {}), "shot:after_tile_left",
    ("maximize_window", {"window_title": "gedit"}), ("list_windows", {}), "shot:after_maximize",
    ("tile_window", {"window_title": "gedit", "side": "right"}), ("list_windows", {}), "shot:after_maximize_tile_right",
    ("press_keys", {"keys": "ctrl+a"}), ("press_keys", {"keys": "ctrl+c"}), "clipboard",
    ("press_keys", {"keys": "ctrl+s"}), "save", ("press_keys", {"keys": "Return"}), "check_saved",
    ("press_keys", {"keys": "ctrl+n"}), ("list_windows", {}),
    ("tile_window", {"window_title": "gedit", "side": "left"}), "shot:ambiguous_two_windows",
    ("close_window", {"window_title": "Untitled Document 1 - gedit"}),  # exact title of the new window
    ("close_window", {"window_title": "typed.txt"}), ("list_windows", {}),
]

X11_STEPS = [
    ("list_windows", {}),
    ("tile_window", {"window_title": "Alpha", "side": "left"}), ("list_windows", {}), "shot:x11_after_tile_left",
    ("maximize_window", {"window_title": "alpha"}), ("list_windows", {}), "shot:x11_after_maximize",
    ("tile_window", {"window_title": "Alpha", "side": "right"}), ("list_windows", {}), "shot:x11_after_tile_right",
    ("maximize_window", {"window_title": "term"}),
    ("close_window", {"window_title": "ALPHA TERM"}), ("list_windows", {}),
]
