import threading
import types

from shells.voice.command_worker import CommandWorker
from shells.voice.speech.chunked_speaker import ChunkedSpeaker
from tests.support.command_worker import await_condition, make_worker, recording_submit, working_tts
from tusk.shared.interrupt_token import InterruptToken
from tusk.shared.schemas.kernel_response import KernelResponse


def _event_submit(events: list[str]):
    def submit(text: str, kind: str = "conversation") -> KernelResponse:
        events.append(f"submit:{text}")
        return KernelResponse(True, "a reply")
    return submit


def _speech_recording_playback(events: list[str], worker_ref) -> object:
    return types.SimpleNamespace(play=lambda wav: events.append(worker_ref().current_speech_text))


def test_submit_runs_while_ack_is_still_playing() -> None:
    release = threading.Event()
    submits: list[str] = []
    playback = types.SimpleNamespace(play=lambda wav: release.wait(timeout=5.0))
    worker = make_worker(recording_submit(submits), tts=working_tts(), playback=playback)
    worker.enqueue("open gedit", "Opening gedit")
    await_condition(lambda: submits == ["open gedit"])
    release.set()
    await_condition(lambda: not worker.is_busy)


def _ack_holding_playback(events: list[str], release: threading.Event, worker_ref) -> object:
    def play(wav: bytes) -> None:
        events.append(worker_ref().current_speech_text)
        if events == ["Opening gedit."]:
            assert release.wait(timeout=5.0)

    return types.SimpleNamespace(play=play)


def test_reply_playback_waits_for_ack_to_finish() -> None:
    events: list[str] = []
    release = threading.Event()
    submits: list[str] = []
    playback = _ack_holding_playback(events, release, lambda: worker)
    worker = make_worker(recording_submit(submits), tts=working_tts(), playback=playback)
    worker.enqueue("open gedit", "Opening gedit")
    await_condition(lambda: submits == ["open gedit"])
    assert "a reply" not in events
    release.set()
    await_condition(lambda: events == ["Opening gedit.", "a reply"])


def test_refrain_is_spoken_with_terminal_punctuation() -> None:
    events: list[str] = []
    playback = _speech_recording_playback(events, lambda: worker)
    worker = make_worker(_event_submit(events), tts=working_tts(), playback=playback)
    worker.enqueue("open gedit", "Opening gedit")
    await_condition(lambda: "Opening gedit." in events)


def test_refrain_keeps_existing_terminal_punctuation() -> None:
    events: list[str] = []
    playback = _speech_recording_playback(events, lambda: worker)
    worker = make_worker(_event_submit(events), tts=working_tts(), playback=playback)
    worker.enqueue("open gedit", "Opening gedit!")
    await_condition(lambda: "Opening gedit!" in events)


def test_refrain_skipped_when_ack_disabled() -> None:
    events: list[str] = []
    playback = _speech_recording_playback(events, lambda: worker)
    worker = make_worker(_event_submit(events), tts=working_tts(), playback=playback, ack_enabled=False)
    worker.enqueue("open gedit", "Opening gedit")
    await_condition(lambda: events == ["submit:open gedit", "a reply"])


def test_empty_refrain_is_not_spoken() -> None:
    events: list[str] = []
    playback = _speech_recording_playback(events, lambda: worker)
    worker = make_worker(_event_submit(events), tts=working_tts(), playback=playback)
    worker.enqueue("open gedit", "")
    await_condition(lambda: events == ["submit:open gedit", "a reply"])


def test_refrain_logged_with_punctuation_when_tts_off() -> None:
    logs: list[tuple] = []
    submits: list[str] = []
    worker = make_worker(recording_submit(submits), tts=None, logs=logs)
    worker.enqueue("open gedit", "Opening gedit")
    await_condition(lambda: submits == ["open gedit"])
    assert ("TUSK", "Opening gedit.") in logs


def test_interrupt_during_ack_does_not_fake_cancellation_of_a_completed_command() -> None:
    # the ack overlaps the run, so a stop during it cannot undo synchronous side effects;
    # the command ran, so report its reply rather than falsely confirming "Stopped."
    token = InterruptToken()
    submits: list[str] = []
    logs: list[tuple] = []
    playback = types.SimpleNamespace(play=lambda wav: token.interrupt())
    worker = make_worker(recording_submit(submits), tts=working_tts(), playback=playback, token=token, logs=logs)
    worker.enqueue("open gedit", "Opening gedit")
    await_condition(lambda: ("TUSK", "a reply") in logs and not worker.is_busy)
    assert submits == ["open gedit"]
    assert ("TUSK", "Stopped.") not in logs


def _worker(calls: list[tuple[str, str]]) -> CommandWorker:
    def submit(text: str, kind: str) -> KernelResponse:
        calls.append((text, kind))
        return KernelResponse(True, "")

    log = types.SimpleNamespace(log=lambda *args: None)
    speaker = ChunkedSpeaker(None, types.SimpleNamespace(play=lambda wav: None), log)
    worker = CommandWorker(submit, speaker, log, InterruptToken())
    worker.start()
    return worker


def test_worker_forwards_kind_to_kernel_submit() -> None:
    calls: list[tuple[str, str]] = []
    _worker(calls).enqueue("open gedit", "Opening gedit", "command")
    await_condition(lambda: calls == [("open gedit", "command")])
