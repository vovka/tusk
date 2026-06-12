import types

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.stages.gatekeeper import LLMGatekeeper
from tusk.shared.schemas.utterance import Utterance


class _RecordingLog:
    def __init__(self) -> None:
        self.tags: list[str] = []

    def log(self, tag: str, message: str, group: str | None = None) -> None:
        self.tags.append(tag)


def test_primary_parse_failure_is_logged_as_error() -> None:
    log = _RecordingLog()
    gatekeeper = LLMGatekeeper(_llm(["no json here at all"]), log)
    result = gatekeeper.evaluate(_utterance("hello"), [])
    assert result.is_directed_at_tusk is False
    assert "ERROR" in log.tags


def test_recovery_parse_failure_is_logged_as_error() -> None:
    log = _RecordingLog()
    responses = ['{"classification":"ambient","cleaned_text":"","reason":"x"}', "still not json"]
    gatekeeper = LLMGatekeeper(_llm(responses), log)
    gatekeeper.process(_utterance("hm"), [], [_candidate()])
    assert "ERROR" in log.tags


def test_total_llm_failure_is_logged_as_error() -> None:
    log = _RecordingLog()
    gatekeeper = LLMGatekeeper(_failing_llm(), log)
    result = gatekeeper.evaluate(_utterance("hello"), [])
    assert result.is_directed_at_tusk is False
    assert "ERROR" in log.tags


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _candidate() -> BufferedUtterance:
    return BufferedUtterance("u1", _utterance("open Firefox"), 1.0, "dropped")


def _llm(responses: list[str]) -> object:
    return types.SimpleNamespace(label="gate", complete_structured=lambda *args: responses.pop(0))


def _failing_llm() -> object:
    def boom(*args: object) -> str:
        raise RuntimeError("provider unavailable")

    return types.SimpleNamespace(label="gate", complete_structured=boom, complete=boom)
