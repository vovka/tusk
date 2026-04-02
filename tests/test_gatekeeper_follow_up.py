import types

from shells.voice.stages.gatekeeper import LLMGatekeeper
from tusk.shared.schemas.utterance import Utterance


def test_recent_forward_adds_follow_up_context_to_next_prompt() -> None:
    prompts: list[str] = []
    llm = _llm(prompts)
    times = iter([100.0, 110.0])
    gatekeeper = LLMGatekeeper(llm, _log(), time_source=lambda: next(times), follow_up_window_seconds=30.0)
    assert gatekeeper.process(_utterance("Tusk open Firefox"), []).text == "open Firefox"
    gatekeeper.evaluate(_utterance("and close it"), [_utterance("open Firefox")])
    assert "Recent context:" in prompts[-1]
    assert "Follow-up utterances may omit the wake word." in prompts[-1]


def test_stale_forward_uses_base_prompt_only() -> None:
    prompts: list[str] = []
    llm = _llm(prompts)
    times = iter([100.0, 141.0])
    gatekeeper = LLMGatekeeper(llm, _log(), time_source=lambda: next(times), follow_up_window_seconds=30.0)
    assert gatekeeper.process(_utterance("Tusk open Firefox"), []).text == "open Firefox"
    gatekeeper.evaluate(_utterance("and close it"), [_utterance("open Firefox")])
    assert "Recent context:" not in prompts[-1]


def _llm(prompts: list[str]) -> object:
    def complete_structured(prompt: str, *_args) -> str:
        prompts.append(prompt)
        return '{"classification":"command","cleaned_text":"open Firefox","reason":"direct"}'

    return types.SimpleNamespace(label="gate", complete_structured=complete_structured)


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
