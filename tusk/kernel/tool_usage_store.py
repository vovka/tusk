import json
import time
from dataclasses import asdict
from pathlib import Path
from tempfile import NamedTemporaryFile

from tusk.kernel.schemas.tool_usage_stats import ToolUsageStats

__all__ = ["ToolUsageStore"]

_HALF_LIFE_DAYS = 14.0


class ToolUsageStore:
    def __init__(self, path: str | Path, now: object | None = None, log: object | None = None) -> None:
        self._path = Path(path)
        self._now = now or time.time
        self._log = log

    def record_success(self, name: str) -> None:
        items = self._load()
        items[name] = self._updated(items.get(name), self._timestamp())
        self._save(items)

    def top_tool_names(self, available: set[str], limit: int = 3) -> list[str]:
        ranked = self._ranked(self._load(), available)
        return [name for name, _ in ranked[:limit]]

    def _ranked(self, items: dict[str, ToolUsageStats], available: set[str]) -> list[tuple[str, float]]:
        now = self._timestamp()
        pairs = [(name, self._decayed(stats, now)) for name, stats in items.items() if name in available]
        return sorted(pairs, key=lambda item: (-item[1], item[0]))

    def _updated(self, stats: ToolUsageStats | None, now: float) -> ToolUsageStats:
        score = self._decayed(stats, now) if stats else 0.0
        count = stats.count if stats else 0
        return ToolUsageStats(score + 1.0, count + 1, now)

    def _decayed(self, stats: ToolUsageStats, now: float) -> float:
        days = max(0.0, now - stats.last_used_at) / 86400.0
        return stats.score * (0.5 ** (days / _HALF_LIFE_DAYS))

    def _load(self) -> dict[str, ToolUsageStats]:
        if not self._path.exists():
            return {}
        try:
            return self._decoded(json.loads(self._path.read_text()))
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            return self._malformed()

    def _decoded(self, payload: dict[str, dict]) -> dict[str, ToolUsageStats]:
        return {name: ToolUsageStats(**item) for name, item in payload.items()}

    def _malformed(self) -> dict[str, ToolUsageStats]:
        if self._log:
            self._log.log("AGENT", f"resetting malformed tool usage file: {self._path}")
        return {}

    def _save(self, items: dict[str, ToolUsageStats]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", dir=self._path.parent, delete=False) as handle:
            json.dump({name: asdict(stats) for name, stats in items.items()}, handle)
            temp_path = Path(handle.name)
        temp_path.replace(self._path)

    def _timestamp(self) -> float:
        return float(self._now())
