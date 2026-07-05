import time

from tusk.shared.llm.llm_retry_policy import LLMRetryPolicy

__all__ = ["LLMRetryRunner"]


class LLMRetryRunner:
    def __init__(
        self,
        attempts: int = 3,
        sleeper: object | None = None,
        policy: LLMRetryPolicy | None = None,
        interrupt_token: object | None = None,
    ) -> None:
        self._attempts = attempts
        self._sleep = sleeper or time.sleep
        self._policy = policy or LLMRetryPolicy()
        self._token = interrupt_token

    def run(self, operation: object, on_retry: object | None = None) -> str:
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
        return attempt < self._attempts and self._policy.should_retry(exc)

    def _handle_retry(self, exc: Exception, attempt: int, on_retry: object | None) -> None:
        if not self._retry(exc, attempt):
            raise exc
        self._notify(on_retry, exc, attempt)
        self._sleep(self._delay(attempt))

    def _notify(self, on_retry: object | None, exc: Exception, attempt: int) -> None:
        if on_retry:
            on_retry(exc, attempt)

    def _delay(self, attempt: int) -> float:
        return 0.5 * attempt
