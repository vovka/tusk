import json
import types

from shells.voice.stages.command_gate_prompt import build_command_gate_prompt
from shells.voice.stages.gatekeeper import LLMGatekeeper
from shells.voice.stages.gatekeeper_support import PRIMARY_SCHEMA
from tusk.shared.schemas.utterance import Utterance


def test_prompt_gains_interrupt_clause_when_busy() -> None:
    prompt = build_command_gate_prompt("", busy=True)
    assert "interrupt" in prompt
    assert "busy" in prompt


def test_prompt_gains_spoken_text_clause_when_speaking() -> None:
    prompt = build_command_gate_prompt("", busy=True, speaking="the weather is sunny")
    assert "the weather is sunny" in prompt
    assert "ambient" in prompt


def test_prompt_has_no_interrupt_clause_when_idle() -> None:
    prompt = build_command_gate_prompt("")
    assert "interrupt" not in prompt


def test_schema_accepts_interrupt_classification() -> None:
    assert "interrupt" in PRIMARY_SCHEMA["properties"]["classification"]["enum"]


def test_interrupt_classification_dispatches_interrupt_when_busy() -> None:
    gatekeeper = _gatekeeper(_llm("interrupt"), busy=True)
    dispatch = gatekeeper.process(_utterance("forget it, that is wrong"), [])
    assert dispatch.action == "interrupt"


def test_interrupt_classification_ignored_when_idle() -> None:
    gatekeeper = _gatekeeper(_llm("interrupt"), busy=False)
    dispatch = gatekeeper.process(_utterance("stop"), [])
    assert dispatch.action == "drop"


def test_busy_state_reaches_prompt() -> None:
    prompts: list[str] = []
    gatekeeper = _gatekeeper(_llm("ambient", prompts), busy=True, speaking="reading a long reply")
    gatekeeper.process(_utterance("anything"), [])
    assert "reading a long reply" in prompts[0]


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _llm(classification: str, prompts: list[str] | None = None) -> object:
    def complete_structured(prompt, text, name, schema, max_tokens):
        if prompts is not None:
            prompts.append(prompt)
        return json.dumps({"classification": classification, "cleaned_text": text, "reason": "test"})
    return types.SimpleNamespace(complete_structured=complete_structured)


def _gatekeeper(llm: object, busy: bool, speaking: str | None = None) -> LLMGatekeeper:
    log = types.SimpleNamespace(log=lambda *args: None)
    return LLMGatekeeper(
        llm, log, is_busy=lambda: busy, current_speech_text=lambda: speaking,
    )
