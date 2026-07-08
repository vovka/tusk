import types

from tests.command_worker_support import await_condition, make_worker, recording_submit, working_tts
from tusk.shared.schemas.kernel_response import KernelResponse


def _event_submit(events: list[str]):
    def submit(text: str) -> KernelResponse:
        events.append(f"submit:{text}")
        return KernelResponse(True, "a reply")
    return submit


def _speech_recording_playback(events: list[str], worker_ref) -> object:
    return types.SimpleNamespace(play=lambda wav: events.append(worker_ref().current_speech_text))


def test_refrain_is_spoken_before_submit() -> None:
    events: list[str] = []
    playback = _speech_recording_playback(events, lambda: worker)
    worker = make_worker(_event_submit(events), tts=working_tts(), playback=playback)
    worker.enqueue("open gedit", "Opening gedit")
    await_condition(lambda: events == ["Opening gedit", "submit:open gedit", "a reply"])


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


def test_refrain_logged_when_tts_off() -> None:
    logs: list[tuple] = []
    submits: list[str] = []
    worker = make_worker(recording_submit(submits), tts=None, logs=logs)
    worker.enqueue("open gedit", "Opening gedit")
    await_condition(lambda: submits == ["open gedit"])
    assert ("TUSK", "Opening gedit") in logs
