import subprocess
import threading

__all__ = ["SpeechPlayback"]


class SpeechPlayback:
    def __init__(self, interrupt_token: object | None = None, poll_seconds: float = 0.1) -> None:
        self._token = interrupt_token
        self._poll = poll_seconds

    def play(self, wav_bytes: bytes) -> None:
        process = subprocess.Popen(["paplay"], stdin=subprocess.PIPE)
        threading.Thread(target=_feed, args=(process, wav_bytes), daemon=True).start()
        self._await(process)

    def _await(self, process: subprocess.Popen) -> None:
        # 30s cap mirrors the old subprocess.run timeout so a wedged audio daemon cannot hang us
        for _ in range(int(30.0 / self._poll)):
            if self._interrupted():
                process.terminate()
            try:
                process.wait(timeout=self._poll)
                return
            except subprocess.TimeoutExpired:
                continue
        process.kill()

    def _interrupted(self) -> bool:
        return self._token is not None and self._token.is_interrupted


def _feed(process: subprocess.Popen, wav_bytes: bytes) -> None:
    try:
        with process.stdin:
            process.stdin.write(wav_bytes)
    except OSError:
        pass
