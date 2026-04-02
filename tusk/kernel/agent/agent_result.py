from dataclasses import dataclass, field

__all__ = ["AgentResult"]


@dataclass(frozen=True)
class AgentResult:
    status: str
    session_id: str
    summary: str
    text: str = ""
    payload: dict[str, object] = field(default_factory=dict)
    artifact_refs: list[dict[str, str]] = field(default_factory=list)

    def reply_text(self) -> str:
        return self.text or self.summary

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "session_id": self.session_id,
            "summary": self.summary,
            "text": self.text,
            "payload": self.payload,
            "artifact_refs": self.artifact_refs,
        }
