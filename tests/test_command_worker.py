import threading
import types

from tests.command_worker_support import (
    await_condition,
    blocking_submit,
    broken_tts,
    failing_then_recording_submit,
    interrupting_submit,
    make_worker,
    recording_submit,
    working_tts,
)
from tusk.shared.interrupt import InterruptToken


def test_enqueue_returns_before_submit_completes() -> None:
    release = threading.Event()
    submits: list[str] = []
    worker = make_worker(blocking_submit(release, submits))
    worker.enqueue("open Firefox")
    assert submits == []
    release.set()
    await_condition(lambda: submits == ["open Firefox"])


def test_commands_run_sequentially_in_order() -> None:
    submits: list[str] = []
    worker = make_worker(recording_submit(submits))
    worker.enqueue("first")
    worker.enqueue("second")
    await_condition(lambda: submits == ["first", "second"])


def test_flush_drops_queued_commands() -> None:
    release, started = threading.Event(), threading.Event()
    submits: list[str] = []
    worker = make_worker(blocking_submit(release, submits, started))
    worker.enqueue("running")
    assert started.wait(timeout=5.0)
    worker.enqueue("queued")
    worker.flush()
    release.set()
    await_condition(lambda: submits == ["running"] and not worker.is_busy)
    assert submits == ["running"]


def test_is_busy_only_while_processing() -> None:
    release = threading.Event()
    worker = make_worker(blocking_submit(release, []))
    assert not worker.is_busy
    worker.enqueue("open Firefox")
    await_condition(lambda: worker.is_busy)
    release.set()
    await_condition(lambda: not worker.is_busy)


def test_current_speech_text_set_only_while_speaking() -> None:
    seen: list[str | None] = []
    playback = types.SimpleNamespace(play=lambda wav: seen.append(worker.current_speech_text))
    worker = make_worker(recording_submit([]), tts=working_tts(), playback=playback)
    worker.enqueue("hi")
    await_condition(lambda: bool(seen))
    assert seen == ["a reply"]
    await_condition(lambda: worker.current_speech_text is None)


def test_token_cleared_when_job_starts() -> None:
    token = InterruptToken()
    token.interrupt()
    worker = make_worker(recording_submit([]), token=token)
    worker.enqueue("hi")
    await_condition(lambda: not token.is_interrupted)


def test_worker_survives_submit_failure() -> None:
    logs: list[tuple] = []
    submits: list[str] = []
    worker = make_worker(failing_then_recording_submit(submits), logs=logs)
    worker.enqueue("boom")
    worker.enqueue("hi")
    await_condition(lambda: submits == ["hi"] and not worker.is_busy)
    assert any(entry[0] == "ERROR" for entry in logs)


def test_token_cleared_before_speaking_after_interrupted_submit() -> None:
    token = InterruptToken()
    interrupted_at_play: list[bool] = []
    playback = types.SimpleNamespace(play=lambda wav: interrupted_at_play.append(token.is_interrupted))
    worker = make_worker(interrupting_submit(token, "Stopped."), tts=working_tts(), playback=playback, token=token)
    worker.enqueue("hi")
    await_condition(lambda: interrupted_at_play == [False])


def test_stale_reply_replaced_when_interrupt_lands_late() -> None:
    token = InterruptToken()
    logs: list[tuple] = []
    worker = make_worker(interrupting_submit(token, "long stale reply"), token=token, logs=logs)
    worker.enqueue("hi")
    await_condition(lambda: ("TUSK", "Stopped.") in logs)
    assert ("TUSK", "long stale reply") not in logs


def test_worker_logs_reply_and_survives_tts_failure() -> None:
    logs: list[tuple] = []
    worker = make_worker(recording_submit([]), tts=broken_tts(), logs=logs)
    worker.enqueue("hi")
    await_condition(lambda: any(entry[0] == "ERROR" for entry in logs))
    assert ("TUSK", "a reply") in logs
