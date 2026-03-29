import json
from pathlib import Path

__all__ = ["SessionEventReader"]


class SessionEventReader:
    def events(self, path: Path) -> list[dict[str, object]]:
        if not path.exists():
            return []
        return [json.loads(line) for line in self._lines(path)]

    def _lines(self, path: Path) -> list[str]:
        text = path.read_text(encoding="utf-8")
        return [line for line in text.splitlines() if line.strip()]
