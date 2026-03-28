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


class LLMRetryPolicy:
    def should_retry(self, exc: Exception) -> bool:
        text = str(exc).lower()
        if "invalid_request_error" in text or "tool_use_failed" in text:
            return False
        return any(term in text for term in _RETRY_TERMS)
