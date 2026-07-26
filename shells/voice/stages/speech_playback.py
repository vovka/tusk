import logging
import subprocess
import threading

__all__ = ["SpeechPlayback"]

logger = logging.getLogger(__name__)


class SpeechPlayback:
    def __init__(self, interrupt_token: object | None = None, poll_seconds: float = 0.1,
                 speed: float = 1.0) -> None:
        self._token = interrupt_token
        self._poll = poll_seconds
        self._speed = speed

    def play(self, wav_bytes: bytes) -> None:
        audio = wav_bytes if self._speed == 1.0 else self._stretch(wav_bytes)
        process = subprocess.Popen(["paplay"], stdin=subprocess.PIPE)
        threading.Thread(target=_feed, args=(process, audio), daemon=True).start()
        self._await(process)

    def _stretch(self, wav_bytes: bytes) -> bytes:
        try:
            return self._run_ffmpeg(wav_bytes)
        except (OSError, subprocess.SubprocessError):
            logger.warning("ffmpeg time-stretch failed; playing at normal speed")
            return wav_bytes

    def _run_ffmpeg(self, wav_bytes: bytes) -> bytes:
        filter_chain = self._atempo_filter_chain(self._speed)
        process = subprocess.Popen(
            ["ffmpeg", "-i", "-", "-af", filter_chain, "-f", "wav", "-"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        stdout, _ = process.communicate(wav_bytes)
        if process.returncode != 0:
            raise subprocess.SubprocessError("ffmpeg exited non-zero")
        return stdout

    @staticmethod
    def _atempo_filter_chain(speed: float) -> str:
        factors = []
        remaining = speed
        while remaining > 2.0:
            factors.append(2.0)
            remaining /= 2.0
        while remaining < 0.5:
            factors.append(0.5)
            remaining /= 0.5
        factors.append(remaining)
        return ",".join(f"atempo={factor}" for factor in factors)

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
