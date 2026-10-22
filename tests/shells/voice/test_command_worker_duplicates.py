import threading

from tests.support.command_worker import await_condition, blocking_submit, make_worker


def _start_blocked_worker(first: str):
    release, started = threading.Event(), threading.Event()
    submits: list[str] = []
    worker = make_worker(blocking_submit(release, submits, started))
    worker.enqueue(first)
    assert started.wait(timeout=5.0)
    return worker, release, submits


def test_duplicate_of_running_command_is_dropped() -> None:
    worker, release, submits = _start_blocked_worker("type a poem")
    worker.enqueue("type a poem")
    worker.enqueue("Type  a poem ")
    release.set()
    await_condition(lambda: not worker.is_busy)
    assert submits == ["type a poem"]


def test_duplicate_of_queued_command_is_dropped() -> None:
    worker, release, submits = _start_blocked_worker("running")
    worker.enqueue("open Firefox")
    worker.enqueue("open  firefox")
    release.set()
    await_condition(lambda: len(submits) == 2 and not worker.is_busy)
    assert submits == ["running", "open Firefox"]


def test_command_can_repeat_after_it_finished() -> None:
    worker, release, submits = _start_blocked_worker("type a poem")
    release.set()
    await_condition(lambda: not worker.is_busy)
    worker.enqueue("type a poem")
    await_condition(lambda: submits == ["type a poem", "type a poem"])


def test_duplicate_differing_only_in_punctuation_is_dropped() -> None:
    # real STT/gate output for one repeated phrase: "open-get-it, and type a short poem" vs "... poem."
    worker, release, submits = _start_blocked_worker("open-get-it, and type a short poem")
    worker.enqueue("open-get-it, and type a short poem.")
    release.set()
    await_condition(lambda: not worker.is_busy)
    assert submits == ["open-get-it, and type a short poem"]
