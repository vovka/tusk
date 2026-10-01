import json
import sys
import threading
import time
from pathlib import Path

from gi.repository import Gio, GLib

from adapters.gnome.server import build_router

TEXT = "Hello from Tusk on Wayland\nПривіт"


class WaylandE2EDriver:
    """Drives gedit in the nested shell only through GnomeToolRouter tools and logs every call."""

    def __init__(self, out_dir: Path, work_dir: Path) -> None:
        self._out = out_dir
        self._saved = work_dir / "typed.txt"
        self._router = build_router()
        self._log = (out_dir / "tool_calls.log").open("w")
        self._bus = Gio.bus_get_sync(Gio.BusType.SESSION)
        # GNOME Shell only serves Screenshot to allow-listed bus names such as org.gnome.Screenshot.
        Gio.bus_own_name_on_connection(self._bus, "org.gnome.Screenshot", Gio.BusNameOwnerFlags.NONE, None, None)
        GLib.MainContext.default().iteration(False)

    def run(self) -> None:
        self._call("press_keys", {"keys": "Escape"})  # the headless shell starts in the overview
        self._call("focus_window", {"window_title": "gedit"})
        self._call("type_text", {"text": TEXT})
        self._shot("after_type")
        self._tool_then_shot("tile_window", {"window_title": "gedit", "side": "left"}, "after_tile")
        self._tool_then_shot("maximize_window", {"window_title": "gedit"}, "after_maximize")
        self._check_clipboard()
        self._check_saved_text()
        self._call("close_window", {"window_title": "gedit"})
        self._call("list_windows", {})

    def _call(self, name: str, arguments: dict) -> dict:
        result = self._router.call(name, arguments)
        self._log.write(json.dumps({"tool": name, "arguments": arguments, "result": result}, ensure_ascii=False) + "\n")
        self._log.flush()
        time.sleep(1)
        return result

    def _tool_then_shot(self, name: str, arguments: dict, shot: str) -> None:
        self._call(name, arguments)
        self._call("list_windows", {})
        self._shot(shot)

    def _shot(self, name: str) -> None:
        # Evidence only, not a tool: GNOME Shell's own screenshot API on the private bus.
        arguments = GLib.Variant("(bbs)", (False, False, str(self._out / f"{name}.png")))
        try:
            reply = self._bus.call_sync("org.gnome.Shell.Screenshot", "/org/gnome/Shell/Screenshot",
                "org.gnome.Shell.Screenshot", "Screenshot", arguments, None, Gio.DBusCallFlags.NONE, 5000, None)
            self._log.write(f"screenshot {name}: {reply.unpack()}\n")
        except GLib.Error as error:
            self._log.write(f"screenshot {name}: {error.message}\n")

    def _check_clipboard(self) -> None:
        self._call("press_keys", {"keys": "ctrl+a"})
        self._call("press_keys", {"keys": "ctrl+c"})
        reader = threading.Thread(target=self._call, args=("read_clipboard", {}), daemon=True)
        reader.start()
        reader.join(5)
        if reader.is_alive():
            self._log.write("read_clipboard: no reply within 5s\n")

    def _check_saved_text(self) -> None:
        self._call("press_keys", {"keys": "ctrl+s"})
        self._call("type_text", {"text": str(self._saved)})
        self._call("press_keys", {"keys": "Return"})
        saved = self._saved.read_text() if self._saved.exists() else None
        verdict = "MATCH" if saved is not None and saved.rstrip("\n") == TEXT else "MISMATCH"
        self._log.write(f"saved text {verdict}: {saved!r}\n")


if __name__ == "__main__":
    WaylandE2EDriver(Path(sys.argv[1]), Path(sys.argv[2])).run()
