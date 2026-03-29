import json
from datetime import datetime, UTC
from pathlib import Path
from uuid import uuid4

from tusk.lib.agent.agent_result import AgentResult
from tusk.lib.agent.agent_session_store import AgentSessionStore
from tusk.lib.agent.session_event_formatter import SessionEventFormatter
from tusk.lib.agent.session_event_reader import SessionEventReader

__all__ = ["FileAgentSessionStore"]


class FileAgentSessionStore(AgentSessionStore):
    def __init__(self, root_dir: str) -> None:
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        self._reader = SessionEventReader()
        self._format = SessionEventFormatter()

    def create_session_id(self) -> str:
        return uuid4().hex

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
        self.append_event(
            session_id,
            "session_started",
            {
                "profile_id": profile_id,
                "parent_session_id": parent_session_id,
                "parent_call_id": parent_call_id,
                "metadata": metadata,
            },
        )

    def append_event(self, session_id: str, event_type: str, data: dict[str, object]) -> None:
        line = json.dumps({"timestamp": self._now(), "type": event_type, "data": data}, default=str)
        path = self._path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")

    def conversation_messages(self, session_id: str) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        for event in self._reader.events(self._path(session_id)):
            if event["type"] != "message_appended":
                continue
            role = str(event["data"].get("role", ""))
            content = str(event["data"].get("content", ""))
            if role and content:
                messages.append({"role": role, "content": content})
        return messages

    def session_digest(self, session_id: str) -> str:
        events = self._reader.events(self._path(session_id))
        return self._format.digest(session_id, events)

    def final_result(self, session_id: str) -> AgentResult | None:
        events = self._reader.events(self._path(session_id))
        return self._format.result(session_id, events)

    def _path(self, session_id: str) -> Path:
        return self._root / f"{session_id}.jsonl"

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
