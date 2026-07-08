import threading
import time
import types
from collections.abc import Callable

from e2e.fake_playback import FakePlayback
from e2e.queue_detector import QueueDetector
from shells.voice.command_worker import CommandWorker
from shells.voice.pipeline import VoicePipeline
from shells.voice.stages.gate.gatekeeper import LLMGatekeeper
from shells.voice.stages.sanitizer import Sanitizer
from shells.voice.stages.transcription_buffer import TranscriptionBuffer
from shells.voice.voice_shell import VoiceShell

__all__ = ["VoiceE2EHarness"]


class VoiceE2EHarness:
    """Real pipeline, gatekeeper, kernel and LLM calls; only mic, STT, TTS and speaker are scripted."""

    def __init__(self, kernel: object, token: object, log: object) -> None:
        self._kernel = kernel
        self.token = token
        self._log = log
        self.detector = QueueDetector()
        self.playback = FakePlayback(token)
        self.replies, self.enqueued, self.interrupts = [], [], 0
        self.worker = self._build_worker()
        self._wrap_enqueue()
        self._shell = VoiceShell(None, log, pipeline=self._build_pipeline(), worker=self.worker)

    def start(self) -> None:
        threading.Thread(target=self._shell.start, args=(self._kernel.submit,), daemon=True).start()

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
        tts = types.SimpleNamespace(synthesize=lambda text: b"E2EWAV")
        log = types.SimpleNamespace(log=self._record_log)
        return CommandWorker(self._kernel.submit, tts, self.playback, log, self.token)

    def _record_log(self, *args: object) -> None:
        if args and args[0] == "TUSK":
            self.replies.append(str(args[1]))
        self._log.log(*args)

    def _wrap_enqueue(self) -> None:
        inner = self.worker.enqueue

        def enqueue(text: str) -> None:
            self.enqueued.append(text)
            inner(text)

        self.worker.enqueue = enqueue

    def _build_pipeline(self) -> VoicePipeline:
        transcriber = types.SimpleNamespace(process=lambda utterance: utterance)
        return VoicePipeline(
            self.detector, transcriber, Sanitizer(self._log), TranscriptionBuffer(self._log),
            self._gatekeeper(), on_interrupt=self._on_interrupt,
        )

    def _gatekeeper(self) -> LLMGatekeeper:
        gk_llm = self._kernel.get_llm_registry().get("gatekeeper")
        return LLMGatekeeper(
            gk_llm, self._log,
            is_busy=lambda: self.worker.is_busy,
            current_speech_text=lambda: self.worker.current_speech_text,
        )

    def _on_interrupt(self) -> None:
        self.interrupts += 1
        self._kernel.request_interrupt()
        self.worker.flush()
