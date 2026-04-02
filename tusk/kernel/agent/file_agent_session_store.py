import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.agent_session_store import AgentSessionStore
from tusk.kernel.agent.session_event_formatter import SessionEventFormatter
from tusk.kernel.agent.session_event_reader import SessionEventReader

__all__ = ["FileAgentSessionStore"]


class FileAgentSessionStore(AgentSessionStore):
    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)
        self._reader = SessionEventReader()
        self._formatter = SessionEventFormatter()

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
        data = self._start_data(session_id, profile_id, parent_session_id, parent_call_id, metadata)
        self.append_event(session_id, "session_started", data)

    def append_event(self, session_id: str, event_type: str, data: dict[str, object]) -> None:
        self._base.mkdir(parents=True, exist_ok=True)
        entry = self._entry(event_type, data)
        with self._path(session_id).open("a") as handle:
            handle.write(json.dumps(entry) + "\n")

    def conversation_messages(self, session_id: str) -> list[dict[str, str]]:
        events = self._reader.read(self._path(session_id))
        return [event["data"] for event in events if event.get("event_type") == "message_appended"]

    def session_digest(self, session_id: str) -> str:
        events = self._reader.read(self._path(session_id))
        return self._formatter.digest(events)

    def final_result(self, session_id: str) -> AgentResult | None:
        events = self._reader.read(self._path(session_id))
        return self._formatter.result(events)

    def _path(self, session_id: str) -> Path:
        return self._base / f"{session_id}.jsonl"

    def _entry(self, event_type: str, data: dict[str, object]) -> dict[str, object]:
        return {"timestamp": datetime.now(timezone.utc).isoformat(), "event_type": event_type, "data": data}

    def _start_data(
        self,
        session_id: str,
        profile_id: str,
        parent_session_id: str,
        parent_call_id: str,
        metadata: dict[str, object],
    ) -> dict[str, object]:
        return {
            "session_id": session_id,
            "profile_id": profile_id,
            "parent_session_id": parent_session_id,
            "parent_call_id": parent_call_id,
            "metadata": metadata,
        }
