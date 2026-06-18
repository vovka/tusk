import types

from tusk.shared.llm import LLMRetryPolicy


class _StatusCodeError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def _response_error(message: str, status_code: int) -> Exception:
    exc = Exception(message)
    exc.response = types.SimpleNamespace(status_code=status_code)
    return exc


def test_retries_when_status_code_nested_in_response() -> None:
    assert LLMRetryPolicy().should_retry(_response_error("upstream broke", 503)) is True


def test_does_not_retry_client_error_nested_in_response() -> None:
    assert LLMRetryPolicy().should_retry(_response_error("missing", 404)) is False


def test_retries_when_status_code_is_rate_limited() -> None:
    assert LLMRetryPolicy().should_retry(_StatusCodeError("request rejected", 429)) is True


def test_retries_when_status_code_is_server_error() -> None:
    assert LLMRetryPolicy().should_retry(_StatusCodeError("upstream broke", 503)) is True


def test_does_not_retry_client_error_status_codes() -> None:
    assert LLMRetryPolicy().should_retry(_StatusCodeError("bad payload", 400)) is False


def test_retries_connection_errors_by_type() -> None:
    assert LLMRetryPolicy().should_retry(ConnectionError("socket closed")) is True


def test_retries_timeout_errors_by_type() -> None:
    assert LLMRetryPolicy().should_retry(TimeoutError("deadline exceeded")) is True


def test_does_not_retry_tool_use_failures_even_with_server_status() -> None:
    assert LLMRetryPolicy().should_retry(_StatusCodeError("tool_use_failed", 500)) is False


def test_keeps_retrying_known_transient_messages() -> None:
    assert LLMRetryPolicy().should_retry(RuntimeError("rate limit exceeded")) is True


def test_does_not_retry_unknown_errors() -> None:
    assert LLMRetryPolicy().should_retry(RuntimeError("something unexpected")) is False
