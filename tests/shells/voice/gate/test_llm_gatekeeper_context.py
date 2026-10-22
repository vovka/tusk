import json
import types

from shells.voice.gate.llm_gatekeeper import LLMGatekeeper
from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.utterance import Utterance


def test_recent_forward_adds_follow_up_context_to_next_prompt() -> None:
    prompts: list[str] = []
    llm = _llm(prompts)
    times = iter([100.0, 110.0, 110.0])
    gatekeeper = LLMGatekeeper(llm, _log(), time_source=lambda: next(times), follow_up_window_seconds=30.0)
    assert gatekeeper.process(_buffered("Tusk open Firefox"), [], []).text == "open Firefox"
    gatekeeper.process(_buffered("and close it"), [_utterance("open Firefox")], [])
    assert "Recent context:" in prompts[-1]
    assert "User: open Firefox" in prompts[-1]
    assert "Follow-up utterances may omit the wake word." in prompts[-1]


def test_stale_forward_uses_base_prompt_only() -> None:
    prompts: list[str] = []
    llm = _llm(prompts)
    times = iter([100.0, 141.0, 141.0])
    gatekeeper = LLMGatekeeper(llm, _log(), time_source=lambda: next(times), follow_up_window_seconds=30.0)
    assert gatekeeper.process(_buffered("Tusk open Firefox"), [], []).text == "open Firefox"
    gatekeeper.process(_buffered("and close it"), [_utterance("open Firefox")], [])
    assert "Recent context:" not in prompts[-1]


def test_command_dispatch_carries_intent_refrain() -> None:
    payload = '{"classification":"command","cleaned_text":"open Firefox","intent":"Opening Firefox"}'
    llm = types.SimpleNamespace(label="gate", complete_structured=lambda prompt, *_args: payload)
    gatekeeper = LLMGatekeeper(llm, _log())
    assert gatekeeper.process(_buffered("Tusk open Firefox"), [], []).intent == "Opening Firefox"


def test_conversation_dispatch_carries_intent_refrain() -> None:
    payload = '{"classification":"conversation","cleaned_text":"tell me a joke","intent":"Telling a joke"}'
    llm = types.SimpleNamespace(label="gate", complete_structured=lambda prompt, *_args: payload)
    gatekeeper = LLMGatekeeper(llm, _log())
    assert gatekeeper.process(_buffered("Tusk tell me a joke"), [], []).intent == "Telling a joke"


def test_interrupt_classification_dispatches_interrupt_when_busy() -> None:
    gatekeeper = _busy_gatekeeper(_classifying_llm("interrupt"), busy=True)
    dispatch = gatekeeper.process(_buffered("forget it, that is wrong"), [], [])
    assert dispatch.action == "interrupt"


def test_interrupt_classification_ignored_when_idle() -> None:
    gatekeeper = _busy_gatekeeper(_classifying_llm("interrupt"), busy=False)
    dispatch = gatekeeper.process(_buffered("stop"), [], [])
    assert dispatch.action == "drop"


def test_busy_state_reaches_prompt() -> None:
    prompts: list[str] = []
    gatekeeper = _busy_gatekeeper(_classifying_llm("ambient", prompts), busy=True, speaking="reading a long reply")
    gatekeeper.process(_buffered("anything"), [], [])
    assert "reading a long reply" in prompts[0]


def test_command_classification_dispatches_with_command_kind() -> None:
    dispatch = _kind_gatekeeper("command").process(_buffered("open gedit"), [], [])
    assert dispatch.kind == "command"
    assert dispatch.text == "open gedit"


def test_conversation_classification_keeps_conversation_kind() -> None:
    dispatch = _kind_gatekeeper("conversation").process(_buffered("hey tusk how are you"), [], [])
    assert dispatch.kind == "conversation"


def _llm(prompts: list[str]) -> object:
    def complete_structured(prompt: str, *_args) -> str:
        prompts.append(prompt)
        return '{"classification":"command","cleaned_text":"open Firefox","reason":"direct"}'

    return types.SimpleNamespace(label="gate", complete_structured=complete_structured)


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _buffered(text: str) -> BufferedUtterance:
    return BufferedUtterance("u1", _utterance(text), 1.0)


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)


def _classifying_llm(classification: str, prompts: list[str] | None = None) -> object:
    def complete_structured(prompt, text, name, schema, max_tokens):
        if prompts is not None:
            prompts.append(prompt)
        return json.dumps({"classification": classification, "cleaned_text": text, "reason": "test"})
    return types.SimpleNamespace(complete_structured=complete_structured)


def _busy_gatekeeper(llm: object, busy: bool, speaking: str | None = None) -> LLMGatekeeper:
    log = types.SimpleNamespace(log=lambda *args: None)
    return LLMGatekeeper(
        llm, log, is_busy=lambda: busy, current_speech_text=lambda: speaking,
    )


def _intent_llm(classification: str) -> object:
    def complete_structured(prompt, text, name, schema, max_tokens):
        return json.dumps({"classification": classification, "cleaned_text": text, "intent": "Doing it", "reason": "test"})
    return types.SimpleNamespace(complete_structured=complete_structured)


def _kind_gatekeeper(classification: str) -> LLMGatekeeper:
    log = types.SimpleNamespace(log=lambda *args: None)
    return LLMGatekeeper(_intent_llm(classification), log)
