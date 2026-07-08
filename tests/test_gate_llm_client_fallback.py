import types

from shells.voice.stages.gate.llm_client import LLMClient


class _Log:
    def log(self, tag: str, message: str, group: str | None = None) -> None: ...


def _llm(fallback_calls: list[int]) -> object:
    def structured(*args: object) -> str:
        raise RuntimeError("empty completion from provider (finish_reason=length)")

    def complete(prompt: str, text: str, max_tokens: int) -> str:
        fallback_calls.append(max_tokens)
        return '{"classification":"ambient","cleaned_text":"","reason":"x"}'

    return types.SimpleNamespace(complete_structured=structured, complete=complete)


def test_fallback_completion_not_weaker_than_structured() -> None:
    fallback_calls: list[int] = []
    LLMClient(_llm(fallback_calls), _Log()).primary("prompt", "hello")
    assert fallback_calls == [512]
