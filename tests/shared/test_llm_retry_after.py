from types import SimpleNamespace

import pytest

from tusk.shared.llm.llm_retry_runner import LLMRetryRunner


class _RateLimited(Exception):
    status_code = 429

    def __init__(self, retry_after: str) -> None:
        super().__init__("Error code: 429 - rate limit")
        self.response = SimpleNamespace(status_code=429, headers={"retry-after": retry_after})


def test_rate_limit_waits_for_the_server_retry_after() -> None:
    sleeps: list[float] = []
    runner = LLMRetryRunner(2, sleeps.append)
    with pytest.raises(_RateLimited):
        runner.run(_raising(_RateLimited("3.5")))
    assert sleeps == [3.5]


def test_retry_after_wait_is_capped() -> None:
    sleeps: list[float] = []
    runner = LLMRetryRunner(2, sleeps.append)
    with pytest.raises(_RateLimited):
        runner.run(_raising(_RateLimited("97")))
    assert sleeps == [20.0]


def test_retry_callback_receives_the_wait() -> None:
    notices: list[tuple[int, float]] = []
    runner = LLMRetryRunner(2, lambda seconds: None)
    with pytest.raises(_RateLimited):
        runner.run(_raising(_RateLimited("3.5")), lambda exc, attempt, wait: notices.append((attempt, wait)))
    assert notices == [(1, 3.5)]


def _raising(error: Exception) -> object:
    def operation() -> str:
        raise error
    return operation


def test_proxy_logs_the_retry_wait() -> None:
    from tusk.shared.llm.llm_proxy import LLMProxy
    lines: list[str] = []
    printer = SimpleNamespace(log=lambda tag, message, group: lines.append(message), show_wait=lambda *_: None, clear_wait=lambda: None)
    inner = SimpleNamespace(label="groq/x", complete=lambda *_: (_ for _ in ()).throw(_RateLimited("3.5")), set_payload_logger=lambda logger: None)
    proxy = LLMProxy(inner, printer, "command_agent", LLMRetryRunner(2, lambda seconds: None))
    with pytest.raises(_RateLimited):
        proxy.complete("system", "user")
    assert any("retry 1 in 3.5s after failure" in line for line in lines)
