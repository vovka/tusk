import types

from tusk.shared.llm import LLMRetryRunner


class _StatusCodeError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def _response_error(message: str, status_code: int) -> Exception:
    exc = Exception(message)
    exc.response = types.SimpleNamespace(status_code=status_code)
    return exc


def _attempts(exc: Exception) -> int:
    count = {"value": 0}
    try:
        LLMRetryRunner(2, lambda seconds: None).run(_counting(count, exc))
    except Exception:
        pass
    return count["value"]


def _counting(count: dict[str, int], exc: Exception) -> object:
    def operation() -> str:
        count["value"] += 1
        raise exc
    return operation


def test_retries_when_status_code_nested_in_response() -> None:
    assert _attempts(_response_error("upstream broke", 503)) == 2


def test_does_not_retry_client_error_nested_in_response() -> None:
    assert _attempts(_response_error("missing", 404)) == 1


def test_retries_when_status_code_is_rate_limited() -> None:
    assert _attempts(_StatusCodeError("request rejected", 429)) == 2


def test_retries_when_status_code_is_server_error() -> None:
    assert _attempts(_StatusCodeError("upstream broke", 503)) == 2


def test_does_not_retry_client_error_status_codes() -> None:
    assert _attempts(_StatusCodeError("bad payload", 400)) == 1


def test_retries_connection_errors_by_type() -> None:
    assert _attempts(ConnectionError("socket closed")) == 2


def test_retries_timeout_errors_by_type() -> None:
    assert _attempts(TimeoutError("deadline exceeded")) == 2


def test_does_not_retry_tool_use_failures_even_with_server_status() -> None:
    assert _attempts(_StatusCodeError("tool_use_failed", 500)) == 1


def test_keeps_retrying_known_transient_messages() -> None:
    assert _attempts(RuntimeError("rate limit exceeded")) == 2


def test_does_not_retry_unknown_errors() -> None:
    assert _attempts(RuntimeError("something unexpected")) == 1
