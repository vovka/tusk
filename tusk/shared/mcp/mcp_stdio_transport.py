import queue
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
        self._stdout_queue: "queue.Queue[str]" = queue.Queue()
        self._stderr_thread = self._spawn(self._drain_stderr)
        self._spawn(self._drain_stdout)

    def write_line(self, line: str) -> None:
        # ponytail: drop any late reply to a timed-out request so it can't be mistaken
        # for the response to this one — the protocol is strictly request/response.
        assert self._process.stdin is not None
        self._discard_pending()
        self._process.stdin.write(line + "\n")
        self._process.stdin.flush()

    def read_line(self) -> str | None:
        try:
            return self._stdout_queue.get(timeout=self._timeout)
        except queue.Empty:
            return None

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

    def _spawn(self, target: object) -> threading.Thread:
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        return thread

    def _discard_pending(self) -> None:
        while True:
            try:
                self._stdout_queue.get_nowait()
            except queue.Empty:
                return

    def _wait_or_kill(self) -> None:
        try:
            self._process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()

    def _drain_stdout(self) -> None:
        # ponytail: one reader keeps lines ordered and bounds threads to one per process,
        # instead of spawning (and leaking) a reader on every request.
        assert self._process.stdout is not None
        for line in self._process.stdout:
            self._stdout_queue.put(line)
        self._stdout_queue.put("")

    def _drain_stderr(self) -> None:
        assert self._process.stderr is not None
        for line in self._process.stderr:
            with self._stderr_lock:
                self._stderr_lines.append(line.rstrip("\n"))
