import subprocess

__all__ = ["X11Windows"]


class X11Windows:
    """Window ids, titles and WM classes on X11, plus the active window and focusing by id."""

    def list_windows(self) -> list[tuple[str, str, str]]:
        output = self._run(["wmctrl", "-l", "-x"])
        listed = (line.split(None, 4) for line in output.splitlines())
        return [(columns[0], columns[4], columns[2]) for columns in listed if len(columns) == 5]

    def active_window_id(self) -> str:
        active = self._run(["xdotool", "getactivewindow"]).strip()
        # wmctrl prints ids as zero-padded hex, xdotool as decimal.
        return f"0x{int(active):08x}" if active.isdigit() else ""

    def focus(self, window_id: str) -> None:
        self._run(["wmctrl", "-i", "-a", window_id])

    def _run(self, command: list[str]) -> str:
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return ""
        return result.stdout if result.returncode == 0 else ""
