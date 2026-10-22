from dataclasses import replace

from tusk.kernel.agent.backends.agent_backend import AgentBackend
from tusk.kernel.agent.backends.backend_request import BackendRequest
from tusk.kernel.agent.backends.backend_result import BackendResult

__all__ = ["FallbackAgentBackend"]


class FallbackAgentBackend(AgentBackend):
    def __init__(self, primary: AgentBackend, fallback: AgentBackend) -> None:
        if primary is None:
            raise ValueError("primary cannot be None")
        if fallback is None:
            raise ValueError("fallback cannot be None")
        self._primary = primary
        self._fallback = fallback

    @property
    def name(self) -> str:
        return self._primary.name

    def run(self, request: BackendRequest) -> BackendResult:
        primary_result = self._primary.run(request)
        if primary_result.status != "failed":
            return primary_result
        return self._fallback_result(request, primary_result)

    def _fallback_result(self, request: BackendRequest, primary_result: BackendResult) -> BackendResult:
        fallback_result = self._fallback.run(request)
        fallback_metadata = fallback_result.metadata or {}
        metadata = {**fallback_metadata, "codex_exec_failure": self._failure_details(primary_result)}
        return replace(fallback_result, metadata=metadata)

    def _failure_details(self, result: BackendResult) -> dict[str, object]:
        return {"status": result.status, "reply": result.reply, "metadata": result.metadata}
