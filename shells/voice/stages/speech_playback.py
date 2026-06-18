import subprocess

__all__ = ["SpeechPlayback"]


class SpeechPlayback:
    def play(self, wav_bytes: bytes) -> None:
        # timeout so a wedged audio daemon cannot hang the pipeline consumer thread
        subprocess.run(["paplay"], input=wav_bytes, check=False, timeout=30)
