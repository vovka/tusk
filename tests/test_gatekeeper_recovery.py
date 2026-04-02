import types

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.stages.gatekeeper import LLMGatekeeper
from tusk.shared.schemas.utterance import Utterance


def test_gatekeeper_recovers_selected_dropped_candidate() -> None:
    dispatch = _gatekeeper([_ambient(), _recover("u2")]).process(_utterance("that was for you"), [], _candidates())
    assert dispatch.action == "forward_recovered"
    assert dispatch.text == "open Firefox"
    assert dispatch.recovered_id == "u2"


def test_gatekeeper_forwards_clarification_when_recovery_is_ambiguous() -> None:
    dispatch = _gatekeeper([_ambient(), _ambiguous()]).process(_utterance("the previous one was for you"), [], _candidates())
    assert dispatch.action == "forward_clarification"
    assert dispatch.text == "the previous one was for you"


def test_gatekeeper_keeps_ambient_drop_when_recovery_finds_no_match() -> None:
    dispatch = _gatekeeper([_ambient(), _none()]).process(_utterance("just chatting"), [], _candidates())
    assert dispatch.action == "drop"
    assert dispatch.text is None


def test_recovered_forward_refreshes_follow_up_window() -> None:
    prompts, times = [], iter([100.0, 110.0])
    gatekeeper = _gatekeeper([_ambient(), _recover("u2"), _command()], prompts, lambda: next(times))
    gatekeeper.process(_utterance("that was for you"), [], _candidates())
    gatekeeper.evaluate(_utterance("and close it"), [_utterance("open Firefox")])
    assert "Recent context:" in prompts[-1]


def _gatekeeper(responses: list[str], prompts: list[str] | None = None, time_source: object | None = None) -> LLMGatekeeper:
    llm = _llm(responses, [] if prompts is None else prompts)
    return LLMGatekeeper(llm, _log(), time_source=time_source or (lambda: 0.0))


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _candidates() -> list[BufferedUtterance]:
    return [BufferedUtterance("u1", _utterance("weather report"), 1.0, "dropped"), BufferedUtterance("u2", _utterance("open Firefox"), 2.0, "dropped")]


def _llm(responses: list[str], prompts: list[str]) -> object:
    def complete_structured(prompt: str, *_args) -> str:
        prompts.append(prompt)
        return responses.pop(0)

    return types.SimpleNamespace(label="gate", complete_structured=complete_structured)


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)


def _ambient() -> str:
    return '{"classification":"ambient","cleaned_text":"","reason":"noise"}'


def _recover(entry_id: str) -> str:
    return f'{{"action":"recover","candidate_id":"{entry_id}","reason":"explicit correction"}}'


def _ambiguous() -> str:
    return '{"action":"ambiguous","candidate_id":"","reason":"too many candidates"}'


def _none() -> str:
    return '{"action":"none","candidate_id":"","reason":"no link"}'


def _command() -> str:
    return '{"classification":"command","cleaned_text":"close it","reason":"follow up"}'
