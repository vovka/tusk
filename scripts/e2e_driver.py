import json
import subprocess
import sys
import threading
import time
from pathlib import Path

from e2e_steps import TEXT, WAYLAND_STEPS, X11_STEPS

from adapters.gnome.server import build_router


class E2EDriver:
    """Runs e2e steps only through GnomeToolRouter tools and logs every call and result."""

    def __init__(self, mode: str, out_dir: Path, work_dir: Path) -> None:
        self._mode = mode
        self._out = out_dir
        self._saved = work_dir / "typed.txt"
        self._router = build_router()
        self._log = (out_dir / f"{mode}_tool_calls.log").open("w")
        self._actions = {"clipboard": self._read_clipboard, "save": self._type_save_path, "check_saved": self._check_saved}

    def run(self) -> None:
        for step in WAYLAND_STEPS if self._mode == "wayland" else X11_STEPS:
            if isinstance(step, tuple):
                self._call(*step)
            elif step.startswith("shot:"):
                self._shot(step[5:])
            else:
                self._actions[step]()

    def _call(self, name: str, arguments: dict) -> None:
        result = self._router.call(name, arguments)
        self._write(json.dumps({"tool": name, "arguments": arguments, "result": result}, ensure_ascii=False))
        time.sleep(1)

    def _write(self, line: str) -> None:
        self._log.write(line + "\n")
        self._log.flush()

    def _shot(self, name: str) -> None:
        path = self._out / f"{name}.png"
        if self._mode == "x11":
            result = subprocess.run(["import", "-window", "root", str(path)], capture_output=True, text=True)
            self._write(f"screenshot {name}: exit={result.returncode} {result.stderr.strip()}")
            return
        # GNOME serves org.gnome.Shell.Screenshot only to allow-listed bus names, so own one.
        command = ["python3", str(Path(__file__).with_name("shell_screenshot.py")), str(path)]
        result = subprocess.run(command, capture_output=True, text=True)
        self._write(f"screenshot {name}: {result.stdout.strip() or result.stderr.strip()}")

    def _read_clipboard(self) -> None:
        reader = threading.Thread(target=self._call, args=("read_clipboard", {}), daemon=True)
        reader.start()
        reader.join(5)
        if reader.is_alive():
            self._write("read_clipboard: no reply within 5s")

    def _type_save_path(self) -> None:
        self._call("type_text", {"text": str(self._saved)})

    def _check_saved(self) -> None:
        saved = self._saved.read_text() if self._saved.exists() else None
        verdict = "MATCH" if saved is not None and saved.rstrip("\n") == TEXT else "MISMATCH"
        self._write(f"saved text {verdict}: {saved!r}")


if __name__ == "__main__":
    E2EDriver(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])).run()
