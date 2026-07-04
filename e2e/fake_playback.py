import time

__all__ = ["FakePlayback"]


class FakePlayback:
    """Pretends to play audio for a fixed duration, honoring the interrupt token like SpeechPlayback."""

    def __init__(self, interrupt_token: object, seconds_per_play: float = 12.0) -> None:
        self._token = interrupt_token
        self.seconds_per_play = seconds_per_play
        self.plays: list[dict] = []

    def play(self, wav_bytes: bytes) -> None:
        record = {"played": 0.0, "interrupted": False}
        self.plays.append(record)
        deadline = time.monotonic() + self.seconds_per_play
        while time.monotonic() < deadline:
            if self._token.is_interrupted:
                record["interrupted"] = True
                return
            time.sleep(0.1)
            record["played"] += 0.1

    @property
    def last(self) -> dict:
        return self.plays[-1] if self.plays else {"played": 0.0, "interrupted": False}
