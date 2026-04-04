import json

__all__ = ["YamlLogFormatter"]


class YamlLogFormatter:
    def format(self, value: object) -> str:
        return "\n".join(self._render(value, 0))

    def _render(self, value: object, indent: int) -> list[str]:
        if isinstance(value, dict):
            return self._dict_lines(value, indent)
        if isinstance(value, list):
            return self._list_lines(value, indent)
        return [self._pad(indent) + self._inline(value)]

    def _dict_lines(self, value: dict[object, object], indent: int) -> list[str]:
        if not value:
            return [self._pad(indent) + "{}"]
        lines: list[str] = []
        for key, item in value.items():
            lines.extend(self._dict_item_lines(str(key), item, indent))
        return lines

    def _dict_item_lines(self, key: str, value: object, indent: int) -> list[str]:
        prefix = self._pad(indent) + f"{key}:"
        if self._is_multiline(value):
            return [prefix + " |-", *self._text_lines(str(value), indent + 2)]
        if self._is_nested(value):
            return [prefix, *self._render(value, indent + 2)]
        return [f"{prefix} {self._inline(value)}"]

    def _list_lines(self, value: list[object], indent: int) -> list[str]:
        if not value:
            return [self._pad(indent) + "[]"]
        lines: list[str] = []
        for item in value:
            lines.extend(self._list_item_lines(item, indent))
        return lines

    def _list_item_lines(self, value: object, indent: int) -> list[str]:
        prefix = self._pad(indent) + "-"
        if self._is_multiline(value):
            return [prefix + " |-", *self._text_lines(str(value), indent + 2)]
        if self._is_nested(value):
            return [prefix, *self._render(value, indent + 2)]
        return [f"{prefix} {self._inline(value)}"]

    def _inline(self, value: object) -> str:
        return json.dumps(value, ensure_ascii=False)

    def _text_lines(self, value: str, indent: int) -> list[str]:
        return [self._pad(indent) + line for line in value.splitlines()]

    def _is_multiline(self, value: object) -> bool:
        return isinstance(value, str) and "\n" in value

    def _is_nested(self, value: object) -> bool:
        return isinstance(value, (dict, list)) and bool(value)

    def _pad(self, indent: int) -> str:
        return " " * indent
