from dataclasses import dataclass, field

from tusk.kernel.agent.backends import AgentBackend, AgentRequest, AgentResult


@dataclass
class RecordingBackend(AgentBackend):
    requests: list[AgentRequest] = field(default_factory=list)

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        return AgentResult(True, "Done.", "next-session")
