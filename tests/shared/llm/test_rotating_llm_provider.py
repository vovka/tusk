import types

from tusk.shared.llm.rotating_llm_provider import RotatingLLMProvider
from tusk.shared.schemas.llm_slot_config import LLMSlotConfig


class _RateLimited(Exception):
    status_code = 429


def _provider(name: str, served: list[str], fail: bool = False) -> object:
    def complete_messages(*args):
        if fail:
            raise _RateLimited(f"Error code: 429 from {name}")
        served.append(name)
        return name

    return types.SimpleNamespace(label=name, complete_messages=complete_messages, set_payload_logger=lambda logger: served.append(f"logger->{name}"))


def test_rotation_round_robins_per_request() -> None:
    served: list[str] = []
    rotation = RotatingLLMProvider([_provider(name, served) for name in ("a", "b", "c")])
    for _ in range(4):
        rotation.complete_messages("prompt", [])
    assert served == ["a", "b", "c", "a"]


def test_rotation_fails_over_to_next_model_on_429() -> None:
    served: list[str] = []
    rotation = RotatingLLMProvider([_provider("a", served, fail=True), _provider("b", served)])
    assert rotation.complete_messages("prompt", []) == "b"


def test_rotation_raises_when_every_model_is_rate_limited() -> None:
    rotation = RotatingLLMProvider([_provider("a", [], fail=True), _provider("b", [], fail=True)])
    try:
        rotation.complete_messages("prompt", [])
    except _RateLimited as exc:
        assert "429" in str(exc)
    else:
        raise AssertionError("expected the last 429 to propagate")


def test_rotation_hands_the_payload_logger_to_every_model() -> None:
    served: list[str] = []
    RotatingLLMProvider([_provider(name, served) for name in ("a", "b")]).set_payload_logger(object())
    assert served == ["logger->a", "logger->b"]


def test_slot_config_single_value_is_unchanged() -> None:
    assert LLMSlotConfig.parse("groq/openai/gpt-oss-120b") == LLMSlotConfig("groq", "openai/gpt-oss-120b")


def test_slot_config_parses_comma_separated_rotation() -> None:
    slot = LLMSlotConfig.parse("groq/qwen/qwen3.8-27b, groq/openai/gpt-oss-20b")
    assert (slot.provider_name, slot.model) == ("groq", "qwen/qwen3.8-27b")
    assert slot.rotation == ("groq/qwen/qwen3.8-27b", "groq/openai/gpt-oss-20b")
