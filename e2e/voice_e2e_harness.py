import threading
import time
import types
from collections.abc import Callable

from e2e.fake_playback import FakePlayback
from e2e.queue_detector import QueueDetector
from shells.voice.command_worker import CommandWorker
from shells.voice.pipeline import VoicePipeline
from shells.voice.speech.chunked_speaker import ChunkedSpeaker
from shells.voice.stages.echo_filter import EchoFilter
from shells.voice.gate.llm_gatekeeper import LLMGatekeeper
from shells.voice.stages.sanitizer import Sanitizer
from shells.voice.stages.transcription_buffer import TranscriptionBuffer
from tusk.kernel.core.kernel_api import KernelAPI
from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.interrupt_token import InterruptToken
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["VoiceE2EHarness"]


class VoiceE2EHarness:
    """Real pipeline, gatekeeper, kernel and LLM calls; only mic, STT, TTS and speaker are scripted."""

    def __init__(self, kernel: KernelAPI, token: InterruptToken, log: LogPrinter) -> None:
        self._kernel = kernel
        self.token = token
        self._log = log
        self.detector = QueueDetector()
        self.playback = FakePlayback(token)
        self.replies: list[str] = []
        self.enqueued: list[str] = []
        self.interrupts = 0
        self.worker = self._build_worker()
        self._pipeline = self._build_pipeline()

    def start(self) -> None:
        self.worker.start()
        threading.Thread(target=self._listen, daemon=True).start()

    def say(self, text: str, duration: float = 2.0) -> None:
        self._log.log("E2E", f"say: {text!r}")
        self.detector.say(text, duration)

    def wait(self, condition: Callable[[], bool], timeout: float, label: str) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(0.05)
        raise AssertionError(f"timeout waiting for: {label}")

    def wait_idle(self, timeout: float = 90.0) -> None:
        self.wait(lambda: not self.worker.is_busy, timeout, "worker idle")

    def _build_worker(self) -> CommandWorker:
        tts = types.SimpleNamespace(synthesize_chunks=lambda text: iter([b"E2EWAV"]))
        speaker = ChunkedSpeaker(tts, self.playback, self._log)
        return CommandWorker(self._submit, speaker, self._log, self.token)

    def _listen(self) -> None:
        for _ in self._pipeline.run(self._enqueue):
            pass

    def _enqueue(self, text: str, refrain: str, kind: str) -> None:
        # counted before the worker can drop a duplicate or flush the queue, so every forwarded echo shows
        self.enqueued.append(text)
        self.worker.enqueue(text, refrain, kind)

    def _submit(self, text: str, kind: str) -> KernelResponse:
        response = self._kernel.submit(text, kind)
        if response.reply:
            self.replies.append(response.reply)
        return response

    def _build_pipeline(self) -> VoicePipeline:
        transcriber = types.SimpleNamespace(process=lambda utterance: utterance)
        return VoicePipeline(
            self.detector, transcriber, Sanitizer(self._log), TranscriptionBuffer(self._log),
            self._gatekeeper(), on_interrupt=self._on_interrupt,
            echo_filter=EchoFilter(lambda: self.worker.recent_speech, self._log),
        )

    def _gatekeeper(self) -> LLMGatekeeper:
        gk_llm = self._kernel.llm_registry.get("gatekeeper")
        return LLMGatekeeper(
            gk_llm, self._log,
            is_busy=lambda: self.worker.is_busy,
            current_speech_text=lambda: self.worker.current_speech_text,
        )

    def _on_interrupt(self) -> None:
        self.interrupts += 1
        self._kernel.request_interrupt()
        self.worker.flush()
