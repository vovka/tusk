import threading

from tests.command_worker_support import await_condition, blocking_submit, make_worker


def _start_blocked_worker(first: str):
    release, started = threading.Event(), threading.Event()
    submits: list[str] = []
    worker = make_worker(blocking_submit(release, submits, started))
    worker.enqueue(first)
    assert started.wait(timeout=5.0)
    return worker, release, submits


def test_latest_command_replaces_older_pending_one() -> None:
    worker, release, submits = _start_blocked_worker("running")
    worker.enqueue("A")
    worker.enqueue("B")
    release.set()
    await_condition(lambda: len(submits) == 2 and not worker.is_busy)
    assert submits == ["running", "B"]


def test_replaced_command_can_be_enqueued_again() -> None:
    worker, release, submits = _start_blocked_worker("running")
    worker.enqueue("A")
    worker.enqueue("B")
    worker.enqueue("A")
    release.set()
    await_condition(lambda: len(submits) == 2 and not worker.is_busy)
    assert submits == ["running", "A"]


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
