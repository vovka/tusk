import queue
import threading
from collections.abc import Callable

from shells.voice.stages.chunked_speaker import ChunkedSpeaker
from tusk.shared.interrupt.interrupt_token import InterruptToken
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["CommandWorker"]


class CommandWorker:
    """Runs kernel commands and speaks replies on its own thread so listening never blocks."""

    def __init__(
        self,
        submit: Callable[[str, str], KernelResponse],
        speaker: ChunkedSpeaker,
        log_printer: LogPrinter,
        interrupt_token: InterruptToken,
        ack_enabled: bool = True,
    ) -> None:
        self._submit = submit
        self._speaker = speaker
        self._log = log_printer
        self._token = interrupt_token
        self._ack_enabled = ack_enabled
        self._queue: queue.Queue[tuple[str, str, str]] = queue.Queue()
        self._busy = threading.Event()

    def start(self) -> None:
        # ponytail: daemon thread, no shutdown protocol — the app runs until process exit
        threading.Thread(target=self._run, daemon=True).start()

    def enqueue(self, text: str, refrain: str = "", kind: str = "conversation") -> None:
        self._queue.put((text, refrain, kind))

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
        return self._speaker.current_text

    @property
    def recent_speech(self) -> list[tuple[str, float]]:
        return self._speaker.recent_speech()

    def _run(self) -> None:
        while True:
            text, refrain, kind = self._queue.get()
            self._busy.set()
            try:
                self._execute(text, refrain, kind)
            except Exception as exc:
                self._log.log("ERROR", f"command failed: {exc}")
            finally:
                self._busy.clear()

    def _execute(self, text: str, refrain: str, kind: str) -> None:
        self._token.clear()
        response = self._submitted_over_ack(text, refrain, kind)
        reply = self._reply_for(response)
        if reply:
            self._log.log("TUSK", reply)
            self._speaker.speak(reply)

    def _submitted_over_ack(self, text: str, refrain: str, kind: str) -> KernelResponse:
        # the ack plays over the kernel run; a stop during it lands via the interrupt token
        ack_playback = self._start_announce(refrain)
        try:
            return self._submit(text, kind)
        finally:
            ack_playback.join()

    def _start_announce(self, refrain: str) -> threading.Thread:
        announce = threading.Thread(target=self._announce, args=(refrain,), daemon=True)
        announce.start()
        return announce

    def _announce(self, refrain: str) -> None:
        if not (self._ack_enabled and refrain):
            return
        spoken = refrain if refrain[-1] in ".!?" else f"{refrain}."
        self._log.log("TUSK", spoken)
        self._speaker.speak(spoken)

    def _reply_for(self, response: KernelResponse) -> str:
        # the kernel run is interrupt-aware and already replies "Stopped." when it actually cancels;
        # trust it so a stop that lands after a command ran doesn't falsely confirm cancellation.
        # clearing the token keeps the reply from self-interrupting its own playback.
        self._token.clear()
        return getattr(response, "reply", "")
