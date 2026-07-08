from tusk.kernel.agent.agent_profile import AgentProfile
from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.agent_run_request import AgentRunRequest

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
            return AgentResult("failed", "", f"unknown profile: {request.profile_id}")
        if len(lineage) >= _MAX_DEPTH:
            return AgentResult("failed", "", "delegation depth exceeded")
        if self._recursive(request, lineage):
            return AgentResult("failed", "", "recursive delegation detected")
        return None

    def child_lineage(
        self,
        request: AgentRunRequest,
        session_id: str,
        lineage: tuple[tuple[str, str, str], ...],
    ) -> tuple[tuple[str, str, str], ...]:
        return (*lineage, (request.profile_id, session_id, request.instruction[:80]))

    def _recursive(self, request: AgentRunRequest, lineage: tuple[tuple[str, str, str], ...]) -> bool:
        return any(entry[0] == request.profile_id for entry in lineage)
