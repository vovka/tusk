from tusk.lib.agent.agent_result import AgentResult

__all__ = ["SessionEventFormatter"]


class SessionEventFormatter:
    def digest(self, events: list[dict[str, object]]) -> str:
        lines = [self._format_event(event) for event in events]
        return "\n".join(lines[-40:])

    def result(self, events: list[dict[str, object]]) -> AgentResult | None:
        for event in reversed(events):
            if event.get("event_type") == "session_finished":
                return self._extract_result(event)
        return None

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
