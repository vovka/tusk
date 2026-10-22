import types

from shells.voice.gate.llm_client import LLMClient


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
    assert fallback_calls == [1024]


def test_structured_budget_leaves_room_for_reasoning() -> None:
    # E2E: gpt-oss-20b spent all 512 tokens reasoning on "Tusk, yes." and returned no JSON, so the yes was lost
    budgets: list[int] = []

    def structured(prompt: str, text: str, name: str, schema: dict, max_tokens: int) -> str:
        budgets.append(max_tokens)
        return "{}"

    llm = types.SimpleNamespace(complete_structured=structured)
    LLMClient(llm, _Log()).primary("prompt", "hello")
    assert budgets == [1024]


def test_structured_only_client_skips_fallback_and_logs_to_its_group() -> None:
    fallback_calls: list[int] = []
    logs: list[tuple] = []
    log = types.SimpleNamespace(log=lambda *a: logs.append(a))
    client = LLMClient(_llm(fallback_calls), log, error_group="speech-stop", allow_fallback=False)
    assert client.complete("prompt", "hello", "speech_stop_gate", {}) == {}
    assert fallback_calls == []
    assert [entry[2] for entry in logs] == ["speech-stop"]


def test_structured_failure_is_logged_as_error() -> None:
    # E2E: a gatekeeper 400 json_validate_failed never surfaced as ERROR
    tags: list[str] = []
    log = types.SimpleNamespace(log=lambda tag, *a: tags.append(tag))
    LLMClient(_llm([]), log).primary("prompt", "hello")
    assert tags[0] == "ERROR"
