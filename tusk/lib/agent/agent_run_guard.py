from tusk.lib.agent.agent_profile import AgentProfile
from tusk.lib.agent.agent_result import AgentResult
from tusk.lib.agent.agent_run_request import AgentRunRequest

__all__ = ["AgentRunGuard"]

_MAX_DEPTH = 4


class AgentRunGuard:
    def validate(
        self,
        request: AgentRunRequest,
        profile: AgentProfile | None,
        lineage: tuple[tuple[str, str, str], ...],
    ) -> AgentResult | None:
        if profile is None:
            return self._failed(request, f"unknown profile: {request.profile_id}")
        if len(lineage) >= _MAX_DEPTH:
            return self._failed(request, "delegation depth exceeded")
        if self._signature(request, profile) in lineage:
            return self._failed(request, "recursive delegation blocked")
        return None

    def child_lineage(
        self,
        request: AgentRunRequest,
        session_id: str,
        lineage: tuple[tuple[str, str, str], ...],
    ) -> tuple[tuple[str, str, str], ...]:
        return (*lineage, (session_id, request.profile_id, self._hash(request.instruction)))

    def _signature(self, request: AgentRunRequest, profile: AgentProfile) -> tuple[str, str, str]:
        return (request.parent_session_id, profile.profile_id, self._hash(request.instruction))

    def _failed(self, request: AgentRunRequest, text: str) -> AgentResult:
        return AgentResult("failed", request.session_id or "", text, text)

    def _hash(self, text: str) -> str:
        return str(abs(hash(text.strip().lower())))
