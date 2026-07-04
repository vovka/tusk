import subprocess
import threading
import time

from tusk.shared.interrupt import InterruptToken

__all__ = ["SpeechPlayback"]


class SpeechPlayback:
    def __init__(
        self,
        interrupt_token: InterruptToken | None = None,
        sleeper: object | None = None,
        poll_interval: float = 0.1,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._token = interrupt_token
        self._sleep = sleeper or time.sleep
        self._poll = poll_interval
        self._timeout = timeout_seconds

    def play(self, wav_bytes: bytes) -> None:
        process = subprocess.Popen(["paplay"], stdin=subprocess.PIPE)
        self._start_writer(process, wav_bytes)
        self._wait(process)

    def _start_writer(self, process: object, wav_bytes: bytes) -> None:
        thread = threading.Thread(target=self._write, args=(process, wav_bytes), daemon=True)
        thread.start()

    def _write(self, process: object, wav_bytes: bytes) -> None:
        if process.stdin is None:
            return
        try:
            process.stdin.write(wav_bytes)
            process.stdin.close()
        except (OSError, ValueError):
            return

    def _wait(self, process: object) -> None:
        deadline = time.monotonic() + self._timeout
        while process.poll() is None:
            if self._interrupted() or time.monotonic() >= deadline:
                self._terminate(process)
                return
            self._sleep(self._poll)

    def _interrupted(self) -> bool:
        return self._token is not None and self._token.is_interrupted

    def _terminate(self, process: object) -> None:
        try:
            process.terminate()
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            self._kill(process)
        except OSError:
            return

    def _kill(self, process: object) -> None:
        try:
            process.kill()
            process.wait()
        except OSError:
            return
