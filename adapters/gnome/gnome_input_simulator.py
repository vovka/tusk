import subprocess

__all__ = ["GnomeInputSimulator"]

_BUTTON_MAP = {"left": 1, "right": 3, "middle": 2}


class GnomeInputSimulator:
    def press_keys(self, keys: str) -> None:
        normalized = self._normalize_keys(keys)
        result = subprocess.run(["xdotool", "key", "--clearmodifiers", "--delay", "0", normalized], check=False)
        self._raise_on_failure(result, normalized)

    def _normalize_keys(self, keys: str) -> str:
        normalized = self._angle_bracket_keys(keys)
        return self._alias_keys(normalized)

    def _angle_bracket_keys(self, keys: str) -> str:
        text = keys.replace("><", "+").replace("<", "").replace(">", "+")
        return text[:-1] if text.endswith("+") else text

    def _alias_keys(self, keys: str) -> str:
        aliases = {"enter": "Return", "esc": "Escape", "ctrl": "ctrl", "shift": "shift", "alt": "alt", "super": "super"}
        parts = [item for item in keys.split("+") if item]
        return "+".join(self._alias_part(parts, aliases, index) for index in range(len(parts)))

    def _alias_part(self, parts: list[str], aliases: dict[str, str], index: int) -> str:
        part = parts[index]
        alias = aliases.get(part.lower(), part)
        return alias.lower() if index < len(parts) - 1 else self._final_key(alias)

    def _final_key(self, key: str) -> str:
        aliases = {"enter": "Return", "esc": "Escape"}
        alias = aliases.get(key.lower(), key)
        return alias.lower() if len(alias) == 1 else alias

    def _raise_on_failure(self, result: object, keys: str) -> None:
        if getattr(result, "returncode", 0) != 0:
            raise RuntimeError(f"failed to press keys: {keys}")

    def type_text(self, text: str) -> None:
        result = subprocess.run(
            ["xdotool", "type", "--delay", "0", "--", text],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(self._type_text_error(result))

    def mouse_click(self, x: int, y: int, button: int, clicks: int) -> None:
        self.mouse_move(x, y)
        subprocess.run(
            ["xdotool", "click", "--repeat", str(clicks), str(button)],
            check=False,
        )

    def mouse_move(self, x: int, y: int) -> None:
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], check=False)

    def mouse_drag(self, from_x: int, from_y: int, to_x: int, to_y: int, button: int) -> None:
        self.mouse_move(from_x, from_y)
        subprocess.run(["xdotool", "mousedown", str(button)], check=False)
        self.mouse_move(to_x, to_y)
        subprocess.run(["xdotool", "mouseup", str(button)], check=False)

    def mouse_scroll(self, direction: str, clicks: int) -> None:
        button = 4 if direction == "up" else 5
        subprocess.run(
            ["xdotool", "click", "--repeat", str(clicks), str(button)],
            check=False,
        )

    def _type_text_error(self, result: object) -> str:
        stderr = getattr(result, "stderr", "").strip()
        suffix = f": {stderr}" if stderr else ""
        return f"failed to type text (exit={result.returncode}){suffix}"
