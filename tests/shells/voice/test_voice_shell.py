import threading
import types
from collections.abc import Iterator

from shells.voice.voice_shell import VoiceShell


def test_start_starts_worker_and_routes_pipeline_target_to_enqueue() -> None:
    started: list[bool] = []
    enqueued: list[str] = []
    worker = _worker(started, enqueued)
    pipeline = types.SimpleNamespace(run=lambda target: [target("open Firefox", "Opening", "command")])
    VoiceShell(pipeline, worker, None, _gate()).start(_must_not_be_called)
    assert started == [True]
    assert enqueued == ["open Firefox"]


def test_stop_ends_the_pipeline_loop() -> None:
    pulled: list[int] = []
    shell = VoiceShell(types.SimpleNamespace(run=lambda target: _results(pulled, lambda: shell.stop())), _worker([], []), None, _gate())
    shell.start(_must_not_be_called)
    assert pulled == [1, 2]


def _results(pulled: list[int], stop: object) -> Iterator[object]:
    pulled.append(1)
    yield object()
    stop()
    pulled.append(2)
    yield object()
    pulled.append(3)
    yield object()


def _worker(started: list[bool], enqueued: list[str]) -> object:
    return types.SimpleNamespace(
        start=lambda: started.append(True), enqueue=lambda text, refrain="", kind="conversation": enqueued.append(text),
    )


def _gate() -> threading.Event:
    gate = threading.Event()
    gate.set()
    return gate


def _must_not_be_called(text: str) -> None:
    raise AssertionError("kernel submit must go through the worker")
