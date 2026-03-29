import json

from tusk.lib.agent.agent_result import AgentResult

__all__ = ["SessionEventFormatter"]


class SessionEventFormatter:
    def digest(self, session_id: str, events: list[dict[str, object]]) -> str:
        lines = [f"Session {session_id} digest:"]
        lines.extend(self._line(event) for event in events)
        return "\n".join(lines[-40:])

    def result(self, session_id: str, events: list[dict[str, object]]) -> AgentResult | None:
        finished = [event for event in events if event["type"] == "session_finished"]
        return self._from_event(session_id, finished[-1]) if finished else None

    def _from_event(self, session_id: str, event: dict[str, object]) -> AgentResult:
        data = dict(event["data"])
        return AgentResult(str(data.get("status", "failed")), session_id, str(data.get("summary", "")), str(data.get("text", "")), dict(data.get("payload", {})), list(data.get("artifact_refs", [])))

    def _line(self, event: dict[str, object]) -> str:
        event_type = str(event["type"])
        data = dict(event["data"])
        if event_type == "message_appended":
            return self._message_line(data)
        if event_type == "session_finished":
            return self._result_line(data)
        return f"- {event_type}: {json.dumps(data, default=str)[:240]}"

    def _message_line(self, data: dict[str, object]) -> str:
        role = str(data.get("role", ""))
        content = str(data.get("content", ""))
        return f"- {role}: {content[:240]}"

    def _result_line(self, data: dict[str, object]) -> str:
        return f"- result: {data.get('status')} / {data.get('summary', '')}"
