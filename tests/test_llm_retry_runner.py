import pytest

from tusk.shared.interrupt import InterruptToken
from tusk.shared.llm import LLMRetryRunner


def test_retry_runner_aborts_before_backoff_when_interrupted() -> None:
    token = InterruptToken()
    attempts: list[int] = []
    sleeps: list[float] = []
    runner = LLMRetryRunner(sleeper=sleeps.append, interrupt_token=token)
    with pytest.raises(RuntimeError, match="interrupted"):
        runner.run(_interrupting_failure(token, attempts))
    assert attempts == [1]
    assert sleeps == []


def _interrupting_failure(token: InterruptToken, attempts: list[int]) -> object:
    def operation() -> str:
        attempts.append(1)
        token.interrupt()
        raise ConnectionError("try again")

    return operation
