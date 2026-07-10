import queue
import threading
from collections.abc import Iterator

from shells.voice.stages.speech_playback import SpeechPlayback
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.tts.interfaces.tts_engine import TTSEngine

__all__ = ["ChunkedSpeaker"]

_END_OF_CHUNKS = object()


class ChunkedSpeaker:
    """Plays each synthesized chunk while the next one is still being synthesized."""

    # latency: first audio starts after one TTS round trip instead of one per chunk

    def __init__(self, tts_engine: TTSEngine | None, playback: SpeechPlayback, log_printer: LogPrinter) -> None:
        self._tts = tts_engine
        self._playback = playback
        self._log = log_printer
        self._current_text: str | None = None

    @property
    def current_text(self) -> str | None:
        return self._current_text

    def speak(self, text: str) -> None:
        if self._tts is None:
            return
        try:
            self._play_all(text)
        except Exception as exc:
            self._log.log("ERROR", f"tts failed: {exc}")

    def _play_all(self, text: str) -> None:
        self._current_text = text
        try:
            for wav_clip in self._prefetched(self._tts.synthesize_chunks(text)):
                self._playback.play(wav_clip)
        finally:
            self._current_text = None

    def _prefetched(self, chunks: Iterator[bytes]) -> Iterator[bytes]:
        buffered: "queue.Queue[object]" = queue.Queue(maxsize=2)
        threading.Thread(target=_synthesize_into, args=(chunks, buffered), daemon=True).start()
        while (item := buffered.get()) is not _END_OF_CHUNKS:
            if isinstance(item, Exception):
                raise item
            yield item


def _synthesize_into(chunks: Iterator[bytes], buffered: "queue.Queue[object]") -> None:
    try:
        for chunk in chunks:
            buffered.put(chunk)
    except Exception as exc:
        buffered.put(exc)
        return
    buffered.put(_END_OF_CHUNKS)
