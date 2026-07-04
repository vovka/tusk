import types

from shells.voice.stages.gatekeeper import LLMGatekeeper
from tusk.shared.schemas.utterance import Utterance


def test_busy_prompt_adds_interrupt_clause() -> None:
    prompts: list[str] = []
    gatekeeper = LLMGatekeeper(_llm(prompts), _log(), is_busy=lambda: True)
    gatekeeper.evaluate(_utterance("forget it"), [])
    assert "currently busy executing a task" in prompts[-1]
    assert "classify it as `interrupt`" in prompts[-1]


def test_speaking_prompt_adds_spoken_text_clause() -> None:
    prompts: list[str] = []
    gatekeeper = LLMGatekeeper(_llm(prompts), _log(), current_speech_text=lambda: "Long reply")
    gatekeeper.evaluate(_utterance("Long reply"), [])
    assert "currently saying aloud: 'Long reply'" in prompts[-1]
    assert "classify them as ambient" in prompts[-1]


def test_interrupt_classification_dispatches_interrupt() -> None:
    payload = '{"classification":"interrupt","cleaned_text":"","reason":"cancel"}'
    gatekeeper = LLMGatekeeper(_llm([], payload), _log(), is_busy=lambda: True)
    assert gatekeeper.process(_utterance("forget that"), []).action == "interrupt"


def test_idle_prompt_omits_interrupt_context() -> None:
    prompts: list[str] = []
    gatekeeper = LLMGatekeeper(_llm(prompts), _log())
    gatekeeper.evaluate(_utterance("stop"), [])
    assert "currently busy executing a task" not in prompts[-1]
    assert "currently saying aloud" not in prompts[-1]


def _llm(prompts: list[str], payload: str | None = None) -> object:
    def complete_structured(prompt: str, *_args) -> str:
        prompts.append(prompt)
        return payload or '{"classification":"ambient","cleaned_text":"","reason":"background"}'

    return types.SimpleNamespace(label="gate", complete_structured=complete_structured)


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
