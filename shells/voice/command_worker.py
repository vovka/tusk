import queue
import threading
from collections.abc import Callable

from shells.voice.stages.speech_playback import SpeechPlayback
from tusk.shared.interrupt.interrupt_token import InterruptToken
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.tts.interfaces.tts_engine import TTSEngine

__all__ = ["CommandWorker"]


class CommandWorker:
    """Runs kernel commands and speaks replies on its own thread so listening never blocks."""

    def __init__(
        self,
        submit: Callable[[str], KernelResponse],
        tts_engine: TTSEngine | None,
        playback: SpeechPlayback,
        log_printer: LogPrinter,
        interrupt_token: InterruptToken,
        ack_enabled: bool = True,
    ) -> None:
        self._submit = submit
        self._tts = tts_engine
        self._playback = playback
        self._log = log_printer
        self._token = interrupt_token
        self._ack_enabled = ack_enabled
        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._busy = threading.Event()
        self._speech_text: str | None = None

    def start(self) -> None:
        # ponytail: daemon thread, no shutdown protocol — the app runs until process exit
        threading.Thread(target=self._run, daemon=True).start()

    def enqueue(self, text: str, refrain: str = "") -> None:
        self._queue.put((text, refrain))

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
            text, refrain = self._queue.get()
            self._busy.set()
            try:
                self._execute(text, refrain)
            except Exception as exc:
                self._log.log("ERROR", f"command failed: {exc}")
            finally:
                self._busy.clear()

    def _execute(self, text: str, refrain: str) -> None:
        self._token.clear()
        self._announce(refrain)
        if self._interrupted_during_ack():
            return
        response = self._submit(text)
        reply = self._reply_for(response)
        if reply:
            self._log.log("TUSK", reply)
            self._speak(reply)

    def _announce(self, refrain: str) -> None:
        # spoken refrain of the request so the user hears TUSK engage before the work runs
        if not (self._ack_enabled and refrain):
            return
        self._log.log("TUSK", refrain)
        self._speak(refrain)

    def _interrupted_during_ack(self) -> bool:
        # a stop during the refrain must abort before the command reaches the kernel
        if not self._token.is_interrupted:
            return False
        self._token.clear()
        self._log.log("TUSK", "Stopped.")
        self._speak("Stopped.")
        return True

    def _reply_for(self, response: KernelResponse) -> str:
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

    def _play(self, reply: str, audio: bytes) -> None:
        self._speech_text = reply
        try:
            self._playback.play(audio)
        finally:
            self._speech_text = None
