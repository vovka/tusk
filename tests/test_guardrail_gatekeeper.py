import types

from tusk.kernel.llm_gatekeeper import LLMGatekeeper
from tusk.kernel.schemas.utterance import Utterance


def test_gatekeeper_uses_structured_output() -> None:
    calls = []
    llm = types.SimpleNamespace(
        label="gate",
        complete_structured=lambda *args: calls.append(args) or '{"classification":"command","cleaned_text":"open Firefox","reason":"wake word"}',
    )
    gatekeeper = LLMGatekeeper(llm, types.SimpleNamespace(log=lambda *a: None))
    result = gatekeeper.evaluate(Utterance("Tusk open Firefox", b"", 1.0), "prompt")
    assert calls and calls[0][2] == "command_gatekeeper"
    assert result.is_directed_at_tusk
    assert result.cleaned_command == "open Firefox"
    assert result.metadata["classification"] == "command"


def test_gatekeeper_treats_conversation_as_directed() -> None:
    llm = types.SimpleNamespace(
        label="gate",
        complete_structured=lambda *a: '{"classification":"conversation","cleaned_text":"how are you","reason":"addressed to tusk"}',
    )
    gatekeeper = LLMGatekeeper(llm, types.SimpleNamespace(log=lambda *a: None))
    result = gatekeeper.evaluate(Utterance("Tusk, how are you?", b"", 1.0), "prompt")
    assert result.is_directed_at_tusk
    assert result.metadata["classification"] == "conversation"


def test_gatekeeper_handles_wrapped_fenced_json() -> None:
    raw = '```json\n[{"arguments":{"classification":"ambient","cleaned_text":"","reason":"noise"}}]\n```'
    llm = types.SimpleNamespace(label="gate", complete_structured=lambda *a: raw)
    gatekeeper = LLMGatekeeper(llm, types.SimpleNamespace(log=lambda *a: None))
    result = gatekeeper.evaluate(Utterance("noise", b"", 1.0), "prompt")
    assert not result.is_directed_at_tusk
    assert result.metadata["classification"] == "ambient"


def test_gatekeeper_falls_back_when_structured_call_fails() -> None:
    llm = types.SimpleNamespace(
        label="gate",
        complete_structured=lambda *a: (_ for _ in ()).throw(RuntimeError("json_validate_failed")),
        complete=lambda *a: '{"classification":"command","cleaned_text":"tell me a joke","reason":"direct request"}',
    )
    gatekeeper = LLMGatekeeper(llm, types.SimpleNamespace(log=lambda *a: None))
    result = gatekeeper.evaluate(Utterance("Great, tell me a joke, please.", b"", 1.0), "prompt")
    assert result.is_directed_at_tusk
    assert result.cleaned_command == "tell me a joke"
