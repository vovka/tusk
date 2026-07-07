from tusk.kernel.agent_backends.agent_request import AgentRequest
from tusk.kernel.agent_backends.agent_result import AgentResult

__all__ = ["ResultMapper"]


class ResultMapper:
    """Maps codex mcp-server tool-call payloads onto AgentResult.

    The codex threadId becomes AgentResult.session_id, which CommandMode feeds
    back as the next request's session_id — that round-trip is what keeps the
    conversation on one codex thread.
    """

    def __init__(self, backend_name: str) -> None:
        self._backend_name = backend_name

    def success(self, request: AgentRequest, payload: dict) -> AgentResult:
        text = self._text(payload)
        if payload.get("isError"):
            return self.failure(request, text or "codex mcp-server reported an error", "failed")
        if not text:
            return self.failure(request, "empty response from codex mcp-server", "failed")
        session_id = self._thread_id(payload) or request.session_id
        return AgentResult(True, text, session_id, self._metadata(request), "success", text, payload)

    def failure(self, request: AgentRequest, message: str, status: str) -> AgentResult:
        return AgentResult(False, message, request.session_id, self._metadata(request), status, message)

    def _thread_id(self, payload: dict) -> str:
        structured = payload.get("structuredContent") or {}
        return str(structured.get("threadId") or "")

    def _text(self, payload: dict) -> str:
        structured = payload.get("structuredContent") or {}
        if structured.get("content"):
            return str(structured["content"])
        items = payload.get("content") or []
        return " ".join(item.get("text", "") for item in items if item.get("type") == "text").strip()

    def _metadata(self, request: AgentRequest) -> dict[str, object]:
        return {**(request.metadata or {}), "backend": self._backend_name, "mode": request.mode}
