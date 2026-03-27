from tusk.kernel.interfaces.conversation_summarizer import ConversationSummarizer
from tusk.lib.llm.interfaces.llm_provider import LLMProvider
from tusk.kernel.schemas.chat_message import ChatMessage

__all__ = ["LLMConversationSummarizer"]

_SUMMARY_PROMPT = (
    "Summarise the following assistant conversation history "
    "into one short paragraph. Keep tool names, key actions, "
    "and outcomes. Omit filler.\n\n"
)


class LLMConversationSummarizer(ConversationSummarizer):
    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm = llm_provider

    def summarize(self, messages: list[ChatMessage]) -> str:
        transcript = _format_transcript(messages)
        prompt = _SUMMARY_PROMPT + transcript
        return self._llm.complete("You are a concise summariser.", prompt)


def _format_transcript(messages: list[ChatMessage]) -> str:
    lines = [f"{m.role}: {m.content}" for m in messages]
    return "\n".join(lines)
