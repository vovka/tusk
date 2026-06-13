import select
import subprocess
import threading
from collections import deque

__all__ = ["MCPStdioTransport"]


class MCPStdioTransport:
    def __init__(self, command: list[str], cwd: str, env: dict | None, response_timeout_seconds: float) -> None:
        self._timeout = response_timeout_seconds
        self._process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self._stderr_lock = threading.Lock()
        self._stderr_lines: deque[str] = deque(maxlen=50)
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

    def write_line(self, line: str) -> None:
        assert self._process.stdin is not None
        self._process.stdin.write(line + "\n")
        self._process.stdin.flush()

    def read_line(self) -> str | None:
        # ponytail: select on the fd relies on the strict one-line-per-request protocol —
        # move to non-blocking reads if a server ever streams extra stdout lines.
        assert self._process.stdout is not None
        ready, _, _ = select.select([self._process.stdout], [], [], self._timeout)
        return self._process.stdout.readline() if ready else None

    def stderr_text(self) -> str:
        self._stderr_thread.join(timeout=0.5)
        with self._stderr_lock:
            return "\n".join(self._stderr_lines).strip()

    def is_running(self) -> bool:
        return self._process.poll() is None

    def stop(self) -> None:
        if not self.is_running():
            return
        self._process.terminate()
        self._wait_or_kill()

    def _wait_or_kill(self) -> None:
        try:
            self._process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()

    def _drain_stderr(self) -> None:
        assert self._process.stderr is not None
        for line in self._process.stderr:
            with self._stderr_lock:
                self._stderr_lines.append(line.rstrip("\n"))
