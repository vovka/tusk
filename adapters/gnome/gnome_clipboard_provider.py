import os
import subprocess

__all__ = ["GnomeClipboardProvider"]

_XCLIP_ARGS = ["-selection", "clipboard"]


class GnomeClipboardProvider:
    def __init__(self) -> None:
        self._wayland = self._is_wayland()

    def read(self) -> str:
        result = subprocess.run(self._read_command(), capture_output=True, text=True, check=False)
        return result.stdout

    def write(self, text: str) -> None:
        subprocess.run(self._write_command(), input=text, text=True, check=False)

    def _read_command(self) -> list[str]:
        return ["wl-paste", "--no-newline"] if self._wayland else ["xclip", *_XCLIP_ARGS, "-o"]

    def _write_command(self) -> list[str]:
        return ["wl-copy"] if self._wayland else ["xclip", *_XCLIP_ARGS]

    def _is_wayland(self) -> bool:
        return os.environ.get("XDG_SESSION_TYPE") == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
