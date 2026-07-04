from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.runtime_result_factory import RuntimeResultFactory
from tusk.shared.interrupt import InterruptToken

__all__ = ["RuntimeCancellation"]


class RuntimeCancellation:
    def __init__(self, results: RuntimeResultFactory, token: InterruptToken | None) -> None:
        self._results = results
        self._token = token

    def check(self, session_id: str) -> AgentResult | None:
        if self._token is None or not self._token.is_interrupted:
            return None
        result = self._results.cancelled(session_id)
        return self._results.persist(session_id, result, result.reply_text())
