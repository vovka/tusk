__all__ = ["ModelFailureReplyBuilder"]


class ModelFailureReplyBuilder:
    def build(self, exc: Exception) -> str:
        text = str(exc).lower()
        if "rate limit" in text or "429" in text:
            return "The model is currently rate limited. Please try again in a few minutes."
        if "json_validate_failed" in text:
            return "I couldn't build a reliable plan for that request. Please try again."
        if "tool_use_failed" in text:
            return "The model returned an invalid tool call. Please try again."
        if "empty completion" in text:
            return "The model returned an empty response. Please try again."
        return "The model is temporarily unavailable. Please try again."
