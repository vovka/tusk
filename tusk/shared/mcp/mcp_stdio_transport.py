import select
import subprocess

from tusk.shared.mcp.mcp_stderr_reader import MCPStderrReader

__all__ = ["MCPStdioTransport"]


class MCPStdioTransport:
    def __init__(self, command: list[str], cwd: str, env: dict | None, response_timeout_seconds: float) -> None:
        self._timeout = response_timeout_seconds
        self._process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self._stderr_reader = MCPStderrReader(self._process.stderr)

    def write_line(self, line: str) -> None:
        assert self._process.stdin is not None
        self._process.stdin.write(line + "\n")
        self._process.stdin.flush()

    def read_line(self) -> str | None:
        assert self._process.stdout is not None
        ready, _, _ = select.select([self._process.stdout], [], [], self._timeout)
        return self._process.stdout.readline() if ready else None

    def stderr_text(self) -> str:
        return self._stderr_reader.text()

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
