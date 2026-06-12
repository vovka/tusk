import threading
from collections import deque
from typing import IO

__all__ = ["MCPStderrReader"]


class MCPStderrReader:
    def __init__(self, stream: IO[str], max_lines: int = 50) -> None:
        self._lines: deque[str] = deque(maxlen=max_lines)
        self._thread = threading.Thread(target=self._drain, args=(stream,), daemon=True)
        self._thread.start()

    def text(self, wait_seconds: float = 0.5) -> str:
        self._thread.join(timeout=wait_seconds)
        return "\n".join(self._lines).strip()

    def _drain(self, stream: IO[str]) -> None:
        for line in stream:
            self._lines.append(line.rstrip("\n"))
