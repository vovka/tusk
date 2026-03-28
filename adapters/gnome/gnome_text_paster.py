import subprocess

__all__ = ["GnomeTextPaster"]


class GnomeTextPaster:
    def paste(self, text: str) -> None:
        subprocess.run(
            ["xdotool", "type", "--delay", "0", "--", text],
            check=False,
        )

    def replace(self, char_count: int, new_text: str) -> None:
        self._delete_backward(char_count)
        self.paste(new_text)

    def _delete_backward(self, char_count: int) -> None:
        if char_count <= 0:
            return
        subprocess.run(
            ["xdotool", "key", "--delay", "0", "--repeat", str(char_count), "BackSpace"],
            check=False,
        )
