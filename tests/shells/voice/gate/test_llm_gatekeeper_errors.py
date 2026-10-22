import types

from shells.voice.gate.llm_gatekeeper import LLMGatekeeper
from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.utterance import Utterance


class _RecordingLog:
    def __init__(self) -> None:
        self.tags: list[str] = []

    def log(self, tag: str, message: str, group: str | None = None) -> None:
        self.tags.append(tag)


def test_primary_parse_failure_is_logged_as_error_and_dropped() -> None:
    log = _RecordingLog()
    gatekeeper = LLMGatekeeper(_llm(["no json here at all"]), log)
    dispatch = gatekeeper.process(_buffered("hello"), [], [])
    assert dispatch.action == "drop"
    assert "ERROR" in log.tags


def test_recovery_parse_failure_is_logged_as_error() -> None:
    log = _RecordingLog()
    responses = ['{"classification":"ambient","cleaned_text":"","reason":"x"}', "still not json"]
    gatekeeper = LLMGatekeeper(_llm(responses), log)
    assert gatekeeper.process(_buffered("no that one"), [], [_candidate()]).action == "drop"
    assert "ERROR" in log.tags


def test_total_llm_failure_is_logged_as_error_and_dropped() -> None:
    log = _RecordingLog()
    gatekeeper = LLMGatekeeper(_failing_llm(), log)
    dispatch = gatekeeper.process(_buffered("hello"), [], [])
    assert dispatch.action == "drop"
    assert "ERROR" in log.tags


def _buffered(text: str) -> BufferedUtterance:
    return BufferedUtterance("u2", Utterance(text, b"", 1.0), 2.0)


def _candidate() -> BufferedUtterance:
    return BufferedUtterance("u1", Utterance("open Firefox", b"", 1.0), 1.0, dropped=True)


def _llm(responses: list[str]) -> object:
    return types.SimpleNamespace(label="gate", complete_structured=lambda *args: responses.pop(0))


def _failing_llm() -> object:
    def boom(*args: object) -> str:
        raise RuntimeError("provider unavailable")

    return types.SimpleNamespace(label="gate", complete_structured=boom, complete=boom)
