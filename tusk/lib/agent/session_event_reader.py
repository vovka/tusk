import json
from pathlib import Path

__all__ = ["SessionEventReader"]


class SessionEventReader:
    def read(self, path: Path) -> list[dict[str, object]]:
        if not path.exists():
            return []
        lines = path.read_text().strip().splitlines()
        return [json.loads(line) for line in lines if line.strip()]
