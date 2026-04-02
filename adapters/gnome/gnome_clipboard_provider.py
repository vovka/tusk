import subprocess

__all__ = ["GnomeClipboardProvider"]

_CLIPBOARD_ARGS = ["-selection", "clipboard"]


class GnomeClipboardProvider:
    def read(self) -> str:
        result = subprocess.run(
            ["xclip", *_CLIPBOARD_ARGS, "-o"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout

    def write(self, text: str) -> None:
        subprocess.run(
            ["xclip", *_CLIPBOARD_ARGS],
            input=text,
            text=True,
            check=False,
        )
