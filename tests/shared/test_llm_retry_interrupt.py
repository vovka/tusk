import pytest

from tusk.shared.interrupt import InterruptToken
from tusk.shared.llm.llm_retry_runner import LLMRetryRunner


def test_interrupted_token_stops_retries_immediately() -> None:
    token = InterruptToken()
    attempts = {"count": 0}
    runner = LLMRetryRunner(sleeper=lambda seconds: None, interrupt_token=token)
    with pytest.raises(ConnectionError):
        runner.run(_failing_operation(attempts, token))
    assert attempts["count"] == 1


def test_uninterrupted_token_keeps_normal_retries() -> None:
    attempts = {"count": 0}
    runner = LLMRetryRunner(sleeper=lambda seconds: None, interrupt_token=InterruptToken())
    with pytest.raises(ConnectionError):
        runner.run(_failing_operation(attempts))
    assert attempts["count"] == 3


def _failing_operation(attempts: dict, token: InterruptToken | None = None) -> object:
    def operation() -> str:
        attempts["count"] += 1
        if token is not None:
            token.interrupt()
        raise ConnectionError("socket closed")
    return operation
