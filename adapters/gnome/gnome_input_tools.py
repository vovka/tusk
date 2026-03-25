__all__ = ["GnomeInputTools"]


class GnomeInputTools:
    def __init__(self, input_simulator: object, text_paster: object) -> None:
        self._input = input_simulator
        self._paster = text_paster

    def press_keys(self, arguments: dict) -> dict:
        self._input.press_keys(arguments["keys"])
        return {"success": True, "message": f"pressed: {arguments['keys']}"}

    def type_text(self, arguments: dict) -> dict:
        text = arguments["text"]
        if self._has_control_chars(text):
            return {"success": False, "message": self._type_text_error()}
        self._input.type_text(text)
        return {"success": True, "message": f"typed literal text ({len(text)} chars)"}

    def replace_recent_text(self, arguments: dict) -> dict:
        self._paster.replace(int(arguments["replace_chars"]), arguments["text"])
        return {"success": True, "message": "replaced"}

    def mouse_click(self, arguments: dict) -> dict:
        self._input.mouse_click(int(arguments["x"]), int(arguments["y"]), self._int(arguments, "button", "1"), self._int(arguments, "clicks", "1"))
        return {"success": True, "message": "clicked"}

    def mouse_move(self, arguments: dict) -> dict:
        self._input.mouse_move(int(arguments["x"]), int(arguments["y"]))
        return {"success": True, "message": "moved"}

    def mouse_drag(self, arguments: dict) -> dict:
        self._input.mouse_drag(self._int(arguments, "from_x"), self._int(arguments, "from_y"), self._int(arguments, "to_x"), self._int(arguments, "to_y"), self._int(arguments, "button", "1"))
        return {"success": True, "message": "dragged"}

    def mouse_scroll(self, arguments: dict) -> dict:
        self._input.mouse_scroll(arguments["direction"], self._int(arguments, "clicks", "1"))
        return {"success": True, "message": "scrolled"}

    def _int(self, arguments: dict, key: str, default: str | None = None) -> int:
        return int(arguments.get(key, default)) if default is not None else int(arguments[key])

    def _has_control_chars(self, text: str) -> bool:
        return any(ord(char) < 32 and char not in "\n\t" for char in text)

    def _type_text_error(self) -> str:
        return "type_text only accepts literal printable text; use press_keys for Enter, Delete, shortcuts, or control keys."
