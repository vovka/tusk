import queue
import threading

__all__ = ["CommandWorker"]


class CommandWorker:
    """Runs kernel commands and speaks replies on its own thread so listening never blocks."""

    def __init__(
        self,
        submit: object,
        tts_engine: object | None,
        playback: object,
        log_printer: object,
        interrupt_token: object,
    ) -> None:
        self._submit = submit
        self._tts = tts_engine
        self._playback = playback
        self._log = log_printer
        self._token = interrupt_token
        self._queue: queue.Queue[str] = queue.Queue()
        self._busy = threading.Event()
        self._speech_text: str | None = None

    def start(self) -> None:
        # ponytail: daemon thread, no shutdown protocol — the app runs until process exit
        threading.Thread(target=self._run, daemon=True).start()

    def enqueue(self, text: str) -> None:
        self._queue.put(text)

    def flush(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return

    @property
    def is_busy(self) -> bool:
        return self._busy.is_set() or not self._queue.empty()

    @property
    def current_speech_text(self) -> str | None:
        return self._speech_text

    def _run(self) -> None:
        while True:
            text = self._queue.get()
            self._busy.set()
            try:
                self._execute(text)
            except Exception as exc:
                self._log.log("ERROR", f"command failed: {exc}")
            finally:
                self._busy.clear()

    def _execute(self, text: str) -> None:
        self._token.clear()
        response = self._submit(text)
        reply = self._reply_for(response)
        if reply:
            self._log.log("TUSK", reply)
            self._speak(reply)

    def _reply_for(self, response: object) -> str:
        # an interrupt during the run means the user wants silence: confirm briefly, never read a stale reply
        if self._token.is_interrupted:
            self._token.clear()
            return "Stopped."
        return getattr(response, "reply", "")

    def _speak(self, reply: str) -> None:
        if self._tts is None:
            return
        try:
            self._play(reply, self._tts.synthesize(reply))
        except Exception as exc:
            self._log.log("ERROR", f"tts failed: {exc}")

    def _play(self, reply: str, audio: object) -> None:
        self._speech_text = reply
        try:
            self._playback.play(audio)
        finally:
            self._speech_text = None
