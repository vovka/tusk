import types

from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate.llm_gatekeeper import LLMGatekeeper
from shells.voice.gate.recovery_gate_prompt import build_recovery_gate_prompt
from tusk.shared.schemas.voice.utterance import Utterance


def test_gatekeeper_recovers_selected_dropped_candidate() -> None:
    dispatch = _gatekeeper([_ambient(), _recover("u2")]).process(_buffered("that was for you"), [], _candidates())
    assert dispatch.action == "forward_recovered"
    assert dispatch.text == "open Firefox"
    assert dispatch.recovered_id == "u2"


def test_gatekeeper_forwards_current_text_when_recovery_is_ambiguous() -> None:
    dispatch = _gatekeeper([_ambient(), _ambiguous()]).process(_buffered("the previous one was for you"), [], _candidates())
    assert dispatch.action == "forward_current"
    assert dispatch.text == "the previous one was for you"


def test_gatekeeper_keeps_ambient_drop_when_recovery_finds_no_match() -> None:
    dispatch = _gatekeeper([_ambient(), _none()]).process(_buffered("just chatting"), [], _candidates())
    assert dispatch.action == "drop"
    assert dispatch.text is None


def test_recovered_forward_refreshes_follow_up_window() -> None:
    prompts, times = [], iter([100.0, 110.0, 110.0])
    gatekeeper = _gatekeeper([_ambient(), _recover("u2"), _command()], prompts, lambda: next(times))
    gatekeeper.process(_buffered("that was for you"), [], _candidates())
    gatekeeper.process(_buffered("and close it"), [_utterance("open Firefox")], [])
    assert "Recent context:" in prompts[-1]


def test_recovery_prompt_normalizes_wake_word_variants() -> None:
    prompt = build_recovery_gate_prompt("", [_variant_candidate()])
    assert "Treat common STT wake-word variants" in prompt
    assert "u3: Hey TASC, how do you do? | normalized: hey tusk how do you do" in prompt


def test_recovery_is_skipped_for_non_referential_ambient_chatter() -> None:
    calls = _counting_gatekeeper([_ambient()]).process(_cue_buffered("the weather is lovely today"), [], _one_candidate())
    assert calls.action == "drop"
    assert _CALL_COUNT["n"] == 1  # only the primary classification, no recovery call


def test_recovery_runs_when_utterance_has_a_reference_cue() -> None:
    _counting_gatekeeper([_ambient(), _none()]).process(_cue_buffered("no the last one"), [], _one_candidate())
    assert _CALL_COUNT["n"] == 2


def test_recovery_runs_for_directed_conversation_without_a_cue() -> None:
    _counting_gatekeeper([_conversation(), _none()]).process(_cue_buffered("good morning friend"), [], _one_candidate())
    assert _CALL_COUNT["n"] == 2


def test_recovery_runs_when_wake_word_present() -> None:
    _counting_gatekeeper([_ambient(), _none()]).process(_cue_buffered("hello there tusk"), [], _one_candidate())
    assert _CALL_COUNT["n"] == 2


_CALL_COUNT = {"n": 0}


def _counting_gatekeeper(responses: list[str]) -> LLMGatekeeper:
    _CALL_COUNT["n"] = 0

    def complete_structured(prompt: str, *_args) -> str:
        _CALL_COUNT["n"] += 1
        return responses.pop(0)

    llm = types.SimpleNamespace(label="gate", complete_structured=complete_structured)
    return LLMGatekeeper(llm, types.SimpleNamespace(log=lambda *a: None), time_source=lambda: 0.0)


def _cue_buffered(text: str) -> BufferedUtterance:
    return BufferedUtterance("u2", _utterance(text), 2.0)


def _one_candidate() -> list[BufferedUtterance]:
    return [BufferedUtterance("u1", _utterance("open Firefox"), 1.0, dropped=True)]


def _gatekeeper(responses: list[str], prompts: list[str] | None = None, time_source: object | None = None) -> LLMGatekeeper:
    llm = _llm(responses, [] if prompts is None else prompts)
    return LLMGatekeeper(llm, _log(), time_source=time_source or (lambda: 0.0))


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _buffered(text: str) -> BufferedUtterance:
    return BufferedUtterance("u9", _utterance(text), 9.0)


def _candidates() -> list[BufferedUtterance]:
    return [BufferedUtterance("u1", _utterance("weather report"), 1.0, dropped=True), BufferedUtterance("u2", _utterance("open Firefox"), 2.0, dropped=True)]


def _variant_candidate() -> BufferedUtterance:
    return BufferedUtterance("u3", _utterance("Hey TASC, how do you do?"), 3.0, dropped=True)


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


def _conversation() -> str:
    return '{"classification":"conversation","cleaned_text":"good morning friend","reason":"chat"}'
