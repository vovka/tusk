import json

__all__ = ["ToolInputJsonParser"]


class ToolInputJsonParser:
    def parse(self, value: object) -> dict | None:
        if isinstance(value, dict):
            return value
        if not isinstance(value, str) or not value.strip():
            return None
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None
