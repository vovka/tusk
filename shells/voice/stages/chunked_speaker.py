import queue
import threading
import time
from collections import deque
from collections.abc import Generator, Iterator

from shells.voice.stages.speech_playback import SpeechPlayback
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.tts.interfaces.tts_engine import TTSEngine

__all__ = ["ChunkedSpeaker"]

_END_OF_CHUNKS = object()
_RECENT_MAX = 8


class ChunkedSpeaker:
    """Plays each synthesized chunk while the next one is still being synthesized."""

    # latency: first audio starts after one TTS round trip instead of one per chunk

    def __init__(self, tts_engine: TTSEngine | None, playback: SpeechPlayback,
                 log_printer: LogPrinter, interrupt_token: object | None = None) -> None:
        self._tts = tts_engine
        self._playback = playback
        self._log = log_printer
        self._token = interrupt_token
        self._current_text: str | None = None
        self._recent: deque[tuple[str, float]] = deque(maxlen=_RECENT_MAX)

    @property
    def current_text(self) -> str | None:
        return self._current_text

    def recent_speech(self) -> list[tuple[str, float]]:
        return list(self._recent)

    def speak(self, text: str) -> None:
        if self._tts is None:
            return
        try:
            self._play_all(text)
        except Exception as exc:
            self._log.log("ERROR", f"tts failed: {exc}")

    def _play_all(self, text: str) -> None:
        clips = self._prefetched(self._tts.synthesize_chunks(text))
        try:
            self._play_clips(clips, text)
        finally:
            clips.close()
            self._current_text = None
            self._recent.append((text, time.monotonic()))

    def _play_clips(self, clips: Iterator[bytes], text: str) -> None:
        for wav_clip in clips:
            if self._interrupted():
                return
            self._current_text = text
            self._playback.play(wav_clip)
            # clear during the silent gap while the next chunk synthesizes, so live speech isn't dropped as echo
            self._current_text = None
            if self._interrupted():
                return

    def _prefetched(self, chunks: Iterator[bytes]) -> Generator[bytes, None, None]:
        buffered: "queue.Queue[object]" = queue.Queue(maxsize=2)
        stop = threading.Event()
        threading.Thread(target=_synthesize_into, args=(chunks, buffered, stop), daemon=True).start()
        try:
            while (item := buffered.get()) is not _END_OF_CHUNKS:
                if isinstance(item, Exception):
                    raise item
                yield item
        finally:
            _shutdown(buffered, stop)

    def _interrupted(self) -> bool:
        return self._token is not None and self._token.is_interrupted


def _synthesize_into(chunks: Iterator[bytes], buffered: "queue.Queue[object]", stop: threading.Event) -> None:
    try:
        for chunk in chunks:
            if stop.is_set():
                return
            _put(buffered, chunk, stop)
    except Exception as exc:
        _put(buffered, exc, stop)
        return
    _put(buffered, _END_OF_CHUNKS, stop)


def _put(buffered: "queue.Queue[object]", item: object, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            buffered.put(item, timeout=0.1)
            return
        except queue.Full:
            continue


def _shutdown(buffered: "queue.Queue[object]", stop: threading.Event) -> None:
    stop.set()
    while True:
        try:
            buffered.get_nowait()
        except queue.Empty:
            return
