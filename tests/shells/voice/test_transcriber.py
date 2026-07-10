import types

from shells.voice.stages.transcriber import Transcriber
from tusk.shared.schemas.utterance import Utterance


def test_transcriber_logs_transcribed_text() -> None:
    logs: list[tuple[str, str, str]] = []
    utterance = Utterance("open Firefox", b"audio", 1.0)
    transcriber = Transcriber(_stt(utterance), 16000, _log(logs))
    result = transcriber.process(Utterance("", b"audio", 1.0))
    assert result == utterance
    assert logs == [("TRANSCRIBER", "text='open Firefox'", "transcriber")]


def _log(logs: list[tuple[str, str, str]]) -> object:
    return types.SimpleNamespace(log=lambda *args: logs.append(args))


def _stt(utterance: Utterance) -> object:
    return types.SimpleNamespace(transcribe=lambda audio, rate: utterance)
