from dataclasses import replace

from tusk.kernel.agent_backends.agent_backend import AgentBackend
from tusk.kernel.agent_backends.agent_request import AgentRequest
from tusk.kernel.agent_backends.agent_result import AgentResult

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

    @property
    def supports_streaming(self) -> bool:
        return self._primary.supports_streaming

    def run(self, request: AgentRequest) -> AgentResult:
        primary_result = self._primary.run(request)
        if primary_result.status != "failed":
            return primary_result
        return self._fallback_result(request, primary_result)

    def _fallback_result(self, request: AgentRequest, primary_result: AgentResult) -> AgentResult:
        fallback_result = self._fallback.run(request)
        metadata = {**fallback_result.metadata, "codex_exec_failure": self._failure_details(primary_result)}
        return replace(fallback_result, metadata=metadata)

    def _failure_details(self, result: AgentResult) -> dict[str, object]:
        return {"status": result.status, "reply": result.reply, "metadata": result.metadata}
