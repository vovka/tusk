import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from tusk.kernel.agent.agent_result import AgentResult

__all__ = ["SessionStore"]


class SessionStore:
    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)

    def create_session_id(self) -> str:
        return uuid.uuid4().hex

    def has_session(self, session_id: str) -> bool:
        return self._path(session_id).exists()

    def start_session(
        self,
        session_id: str,
        profile_id: str,
        parent_session_id: str,
        parent_call_id: str,
        metadata: dict[str, object],
    ) -> None:
        data = {
            "session_id": session_id,
            "profile_id": profile_id,
            "parent_session_id": parent_session_id,
            "parent_call_id": parent_call_id,
            "metadata": metadata,
        }
        self.append_event(session_id, "session_started", data)

    def append_event(self, session_id: str, event_type: str, data: dict[str, object]) -> None:
        self._base.mkdir(parents=True, exist_ok=True)
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "event_type": event_type, "data": data}
        with self._path(session_id).open("a") as handle:
            handle.write(json.dumps(entry) + "\n")

    def conversation_messages(self, session_id: str) -> list[dict[str, str]]:
        events = self._read_events(session_id)
        return [event["data"] for event in events if event.get("event_type") == "message_appended"]

    def session_digest(self, session_id: str) -> str:
        lines = [self._format_event(event) for event in self._read_events(session_id)]
        return "\n".join(lines[-40:])

    def final_result(self, session_id: str) -> AgentResult | None:
        for event in reversed(self._read_events(session_id)):
            if event.get("event_type") == "session_finished":
                return self._extract_result(event)
        return None

    def _path(self, session_id: str) -> Path:
        return self._base / f"{session_id}.jsonl"

    def _read_events(self, session_id: str) -> list[dict[str, object]]:
        path = self._path(session_id)
        if not path.exists():
            return []
        lines = path.read_text().strip().splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def _format_event(self, event: dict[str, object]) -> str:
        event_type = event.get("event_type", "unknown")
        data = event.get("data", {})
        return f"[{event_type}] {self._summary_of(data)}"

    def _summary_of(self, data: dict[str, object]) -> str:
        if "message" in data:
            return str(data["message"])[:120]
        if "summary" in data:
            return str(data["summary"])[:120]
        return str(data)[:120]

    def _extract_result(self, event: dict[str, object]) -> AgentResult:
        data = event.get("data", {})
        return AgentResult(
            status=str(data.get("status", "unknown")),
            session_id=str(data.get("session_id", "")),
            summary=str(data.get("summary", "")),
            text=str(data.get("text", "")),
            payload=dict(data.get("payload", {})),
            artifact_refs=list(data.get("artifact_refs", [])),
        )
