__all__ = ["ModelFailureReplyBuilder"]


class ModelFailureReplyBuilder:
    def build(self, exc: Exception) -> str:
        text = str(exc).lower()
        if "rate limit" in text or "429" in text:
            return "The model is currently rate limited. Please try again in a few minutes."
        if "empty completion" in text:
            return "The model returned an empty response. Please try again."
        return "The model is temporarily unavailable. Please try again."
