from dataclasses import dataclass, field

from tusk.kernel.agent.backends import AgentBackend, BackendRequest, BackendResult


@dataclass
class RecordingBackend(AgentBackend):
    requests: list[BackendRequest] = field(default_factory=list)

    def run(self, request: BackendRequest) -> BackendResult:
        self.requests.append(request)
        return BackendResult(True, "Done.", "next-session")
