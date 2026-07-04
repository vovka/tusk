import queue
import threading
from collections.abc import Callable

from tusk.shared.interrupt import InterruptToken
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["CommandWorker"]


class CommandWorker:
    def __init__(self, tts_engine: object | None, playback: object, log: object, interrupt_token: InterruptToken) -> None:
        self._tts = tts_engine
        self._playback = playback
        self._log = log
        self._token = interrupt_token
        self._queue: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        self._busy = False
        self._speech_text: str | None = None
        self._thread: threading.Thread | None = None

    @property
    def is_busy(self) -> bool:
        with self._lock:
            return self._busy or not self._queue.empty()

    @property
    def current_speech_text(self) -> str | None:
        with self._lock:
            return self._speech_text

    def start(self, submit: Callable[[str], KernelResponse]) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, args=(submit,), daemon=True)
        self._thread.start()

    def enqueue(self, text: str) -> None:
        self._queue.put(text)

    def flush(self) -> None:
        while self._drop_one():
            pass

    def _drop_one(self) -> bool:
        try:
            self._queue.get_nowait()
            self._queue.task_done()
            return True
        except queue.Empty:
            return False

    def _run(self, submit: Callable[[str], KernelResponse]) -> None:
        while True:
            text = self._queue.get()
            self._handle(text, submit)
            self._queue.task_done()

    def _handle(self, text: str, submit: Callable[[str], KernelResponse]) -> None:
        self._token.clear()
        self._set_busy(True)
        try:
            self._reply(submit(text).reply)
        finally:
            self._set_speech(None)
            self._set_busy(False)

    def _reply(self, reply: str) -> None:
        if not reply:
            return
        self._log.log("TUSK", reply)
        self._speak(reply)

    def _speak(self, reply: str) -> None:
        if self._tts is None:
            return
        try:
            self._play_reply(reply)
        except Exception as exc:
            self._log.log("ERROR", f"tts failed: {exc}")

    def _play_reply(self, reply: str) -> None:
        audio = self._tts.synthesize(reply)
        self._set_speech(reply)
        self._playback.play(audio)

    def _set_busy(self, busy: bool) -> None:
        with self._lock:
            self._busy = busy

    def _set_speech(self, text: str | None) -> None:
        with self._lock:
            self._speech_text = text
