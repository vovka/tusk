import time
from collections.abc import Callable
from typing import TypeVar

from tusk.shared.interrupt_token import InterruptToken

__all__ = ["LLMRetryRunner"]

# a TPM 429 asks for a few seconds; a TPD 429 asks for minutes, which a voice command cannot wait for
_MAX_RETRY_AFTER_SECONDS = 20.0
_RETRY_TERMS = (
    "429",
    "500",
    "502",
    "503",
    "504",
    "api fail",
    "connection",
    "rate limit",
    "service unavailable",
    "temporarily unavailable",
    "timeout",
    "timed out",
)
_BLOCKED_TERMS = ("invalid_request_error", "tool_use_failed")
_BLOCKED_STATUS_CODES = frozenset({400, 401, 403, 404, 422})
T = TypeVar("T")
RetryListener = Callable[[Exception, int, float], None]


class LLMRetryRunner:
    def __init__(self, attempts: int = 3, sleeper: Callable[[float], None] | None = None, interrupt_token: InterruptToken | None = None) -> None:
        self._attempts = attempts
        self._sleep = sleeper or time.sleep
        self._token = interrupt_token

    def run(self, operation: Callable[[], T], on_retry: RetryListener | None = None) -> T:
        last_error = None
        for attempt in range(1, self._attempts + 1):
            try:
                return operation()
            except Exception as exc:
                last_error = exc
                self._handle_retry(exc, attempt, on_retry)
        raise last_error

    def _retry(self, exc: Exception, attempt: int) -> bool:
        if self._token is not None and self._token.is_interrupted:
            return False
        return attempt < self._attempts and self._should_retry(exc)

    def _should_retry(self, exc: Exception) -> bool:
        if self._blocked(exc):
            return False
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return True
        status_code = self._status_code(exc)
        if status_code is not None:
            return status_code == 429 or status_code >= 500
        return any(term in str(exc).lower() for term in _RETRY_TERMS)

    def _blocked(self, exc: Exception) -> bool:
        text = str(exc).lower()
        if any(term in text for term in _BLOCKED_TERMS):
            return True
        return self._status_code(exc) in _BLOCKED_STATUS_CODES

    def _status_code(self, exc: Exception) -> int | None:
        code = getattr(exc, "status_code", None)
        if code is None:
            code = getattr(getattr(exc, "response", None), "status_code", None)
        return code if isinstance(code, int) else None

    def _handle_retry(self, exc: Exception, attempt: int, on_retry: RetryListener | None) -> None:
        if not self._retry(exc, attempt):
            raise exc
        delay = self._delay(exc, attempt)
        self._notify(on_retry, exc, attempt, delay)
        self._sleep(delay)

    def _notify(self, on_retry: RetryListener | None, exc: Exception, attempt: int, delay: float) -> None:
        if on_retry:
            on_retry(exc, attempt, delay)

    def _delay(self, exc: Exception, attempt: int) -> float:
        headers = getattr(getattr(exc, "response", None), "headers", None) or {}
        try:
            return min(float(headers.get("retry-after", "")), _MAX_RETRY_AFTER_SECONDS)
        except ValueError:
            return 0.5 * attempt
