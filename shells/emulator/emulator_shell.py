import os
import time

__all__ = ["EmulatorShell"]


class EmulatorShell:
    """Replays a scripted transcript into the kernel, standing in for voice input."""

    def __init__(self, sleep: object = time.sleep) -> None:
        self._sleep = sleep

    def start(self, submit: object) -> None:
        for utterance in self._utterances():
            self._speak(utterance, submit)
            self._sleep(self._pause())

    def stop(self) -> None:
        return None

    def _utterances(self) -> list[str]:
        with open(self._path(), encoding="utf-8") as handle:
            return self._spoken(handle.readlines())

    def _spoken(self, lines: list[str]) -> list[str]:
        stripped = (line.strip() for line in lines)
        return [line for line in stripped if line and not line.startswith("#")]

    def _speak(self, utterance: str, submit: object) -> None:
        print(f"🎙️  {utterance}", flush=True)
        reply = submit(utterance).reply
        if reply:
            print(f"   ↳ {reply}", flush=True)

    def _path(self) -> str:
        return os.environ["TUSK_TRANSCRIPT"]

    def _pause(self) -> float:
        return float(os.environ.get("TUSK_UTTERANCE_PAUSE", "3"))
