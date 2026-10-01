import json

__all__ = ["FakeBus"]

_WINDOWS = [
    {"id": 7, "title": "Notes - gedit", "wm_class": "gedit", "focused": True, "x": 1, "y": 2, "width": 3, "height": 4},
    {"id": 9, "title": "Terminal", "wm_class": "tilix", "focused": False, "x": 0, "y": 0, "width": 5, "height": 6},
]


class FakeBus:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[object]]] = []

    def call(self, method: str, arguments: list[object]) -> None:
        self.calls.append((method, arguments))

    def call_string(self, method: str) -> str:
        return json.dumps(_WINDOWS)
