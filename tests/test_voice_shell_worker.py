import types

from shells.voice.voice_shell import VoiceShell


def test_voice_shell_routes_submits_through_worker() -> None:
    started: list[bool] = []
    enqueued: list[str] = []
    worker = types.SimpleNamespace(
        start=lambda: started.append(True),
        enqueue=lambda text: enqueued.append(text),
    )
    pipeline = types.SimpleNamespace(run=lambda submit: [submit("open Firefox")])
    log = types.SimpleNamespace(log=lambda *args: None)
    VoiceShell(None, log, pipeline=pipeline, worker=worker).start(_must_not_be_called)
    assert started == [True]
    assert enqueued == ["open Firefox"]


def _must_not_be_called(text: str) -> None:
    raise AssertionError("kernel submit must go through the worker")
