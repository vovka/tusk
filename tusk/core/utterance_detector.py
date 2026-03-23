from collections.abc import Iterator

import webrtcvad

from tusk.core.audio_capture import AudioCapture
from tusk.interfaces.log_printer import LogPrinter
from tusk.schemas.utterance import Utterance

__all__ = ["UtteranceDetector"]

_SILENCE_FRAMES_THRESHOLD = 20
_MIN_VOICED_FRAMES = 5


class UtteranceDetector:
    def __init__(
        self,
        audio_capture: AudioCapture,
        sample_rate: int,
        aggressiveness: int,
        log_printer: LogPrinter,
    ) -> None:
        self._audio = audio_capture
        self._sample_rate = sample_rate
        self._vad = webrtcvad.Vad(aggressiveness)
        self._log = log_printer

    def stream_utterances(self) -> Iterator[Utterance]:
        voiced_frames: list[bytes] = []
        silence_count = 0
        for frame in self._audio.stream_frames():
            is_speech = self._vad.is_speech(frame, self._sample_rate)
            if is_speech:
                if not voiced_frames:
                    self._log.log("VAD", "speech started")
                voiced_frames.append(frame)
                silence_count = 0
            elif voiced_frames:
                silence_count += 1
                if silence_count >= _SILENCE_FRAMES_THRESHOLD:
                    if len(voiced_frames) >= _MIN_VOICED_FRAMES:
                        self._log.log("VAD", f"utterance complete ({len(voiced_frames)} frames)")
                        yield self._build_utterance(voiced_frames)
                    else:
                        self._log.log("VAD", f"too short, discarded ({len(voiced_frames)} frames)")
                    voiced_frames = []
                    silence_count = 0

    def _build_utterance(self, frames: list[bytes]) -> Utterance:
        raw = b"".join(frames)
        duration = len(frames) * 0.030
        return Utterance(text="", audio_frames=raw, duration_seconds=duration)
