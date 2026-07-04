import pytest

from tusk.shared.interrupt import InterruptToken
from tusk.shared.llm.llm_retry_runner import LLMRetryRunner


def test_interrupted_token_stops_retries_immediately() -> None:
    token = InterruptToken()
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        token.interrupt()
        raise ConnectionError("socket closed")

    runner = LLMRetryRunner(sleeper=lambda seconds: None, interrupt_token=token)
    with pytest.raises(ConnectionError):
        runner.run(operation)
    assert attempts["count"] == 1


def test_uninterrupted_token_keeps_normal_retries() -> None:
    attempts = {"count": 0}

    def operation() -> str:
        attempts["count"] += 1
        raise ConnectionError("socket closed")

    runner = LLMRetryRunner(sleeper=lambda seconds: None, interrupt_token=InterruptToken())
    with pytest.raises(ConnectionError):
        runner.run(operation)
    assert attempts["count"] == 3
