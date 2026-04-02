import types

from shells.voice.pipeline import VoicePipeline
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.utterance import Utterance


def test_pipeline_submits_directed_text() -> None:
    submits: list[str] = []
    pipeline = VoicePipeline(_detector("audio"), _transcriber("open Firefox"), _sanitizer(), _buffer(), _gatekeeper("open Firefox"))
    results = list(pipeline.run(_submitter(submits)))
    assert submits == ["open Firefox"]
    assert results == [KernelResponse(True, "done")]


def test_pipeline_drops_sanitized_phantoms() -> None:
    pipeline = VoicePipeline(_detector("audio"), _transcriber("ghost"), _dropper(), _buffer(), _gatekeeper("open Firefox"))
    assert list(pipeline.run(_submitter([]))) == []


def test_pipeline_drops_ambient_speech() -> None:
    pipeline = VoicePipeline(_detector("audio"), _transcriber("background"), _sanitizer(), _buffer(), _gatekeeper(None))
    assert list(pipeline.run(_submitter([]))) == []


def _buffer() -> object:
    return types.SimpleNamespace(process=lambda utterance: utterance, recent=lambda count: [])


def _detector(audio: str) -> object:
    utterance = Utterance("", audio.encode(), 1.0)
    return types.SimpleNamespace(stream_utterances=lambda: iter([utterance]))


def _dropper() -> object:
    return types.SimpleNamespace(process=lambda utterance: None)


def _gatekeeper(command: str | None) -> object:
    return types.SimpleNamespace(process=lambda utterance, recent: command)


def _sanitizer() -> object:
    return types.SimpleNamespace(process=lambda utterance: utterance)


def _submitter(submits: list[str]) -> object:
    return lambda text: submits.append(text) or KernelResponse(True, "done")


def _transcriber(text: str) -> object:
    utterance = Utterance(text, b"audio", 1.0)
    return types.SimpleNamespace(process=lambda input_utterance: utterance)
