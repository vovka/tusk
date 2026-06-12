__all__ = ["LLMRetryPolicy"]

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


class LLMRetryPolicy:
    def should_retry(self, exc: Exception) -> bool:
        if self._blocked(exc):
            return False
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return True
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code == 429 or status_code >= 500
        return any(term in str(exc).lower() for term in _RETRY_TERMS)

    def _blocked(self, exc: Exception) -> bool:
        text = str(exc).lower()
        if any(term in text for term in _BLOCKED_TERMS):
            return True
        return getattr(exc, "status_code", None) in _BLOCKED_STATUS_CODES
