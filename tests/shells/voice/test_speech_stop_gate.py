import json
import types

from shells.voice.stages.gate.speech_stop_gate import SpeechStopGate


def test_stop_intent_returns_true() -> None:
    gate, prompts = _gate(json.dumps({"stop": True, "reason": "user wants silence"}))
    assert gate.should_stop("okay okay enough", "the weather report")
    assert "the weather report" in prompts[0]


def test_echo_of_spoken_text_returns_false() -> None:
    gate, _ = _gate(json.dumps({"stop": False, "reason": "echo"}))
    assert not gate.should_stop("the weather report", "the weather report")


def test_prompt_requires_unambiguous_stop_intent() -> None:
    gate, prompts = _gate(json.dumps({"stop": False, "reason": "self-talk"}))
    gate.should_stop("I'm going to go", "the weather report")
    assert "sole," in prompts[0] and "unambiguous meaning" in prompts[0]
    assert "I'm going to go" in prompts[0]


def test_llm_failure_returns_false() -> None:
    def broken(*args: object) -> str:
        raise RuntimeError("llm down")
    llm = types.SimpleNamespace(complete_structured=broken, complete=broken)
    log = types.SimpleNamespace(log=lambda *args: None)
    assert not SpeechStopGate(llm, log).should_stop("stop", "reply")


def _gate(raw: str) -> tuple[SpeechStopGate, list[str]]:
    prompts: list[str] = []
    def complete_structured(prompt, text, name, schema, max_tokens):
        prompts.append(prompt)
        return raw
    llm = types.SimpleNamespace(complete_structured=complete_structured)
    log = types.SimpleNamespace(log=lambda *args: None)
    return SpeechStopGate(llm, log), prompts
