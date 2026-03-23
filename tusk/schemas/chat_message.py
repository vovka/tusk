from dataclasses import dataclass

__all__ = ["ChatMessage"]

_SUMMARY_PREFIX = "Previous context summary: "


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str

    @property
    def is_summary(self) -> bool:
        return self.content.startswith(_SUMMARY_PREFIX)

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}
