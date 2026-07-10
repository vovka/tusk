import atexit
import threading

from tusk.kernel.agent.backends.agent_backend import AgentBackend
from tusk.kernel.agent.backends.agent_request import AgentRequest
from tusk.kernel.agent.backends.agent_result import AgentResult
from tusk.kernel.agent.backends.backend_run_logger import BackendRunLogger
from tusk.kernel.agent.backends.codex_mcp.call_builder import CallBuilder
from tusk.kernel.agent.backends.codex_mcp.client import Client
from tusk.kernel.agent.backends.codex_mcp.result_mapper import ResultMapper
from tusk.kernel.agent.backends.codex_prompt_builder import CodexPromptBuilder
from tusk.shared.logging.interfaces.log_printer import LogPrinter

__all__ = ["CodexMcpAgentBackend"]


class CodexMcpAgentBackend(AgentBackend):
    """Drives one persistent `codex mcp-server` process across turns."""

    def __init__(self, config: object, log_printer: LogPrinter) -> None:
        self._config = config
        self._prompt_builder = CodexPromptBuilder()
        self._call_builder = CallBuilder(config)
        self._mapper = ResultMapper(self.name)
        self._run_logger = BackendRunLogger(log_printer, self.name)
        self._lock = threading.Lock()
        self._client: Client | None = None
        atexit.register(self._reset_client)

    @property
    def name(self) -> str:
        return "codex_mcp"

    @property
    def supports_streaming(self) -> bool:
        return False

    def run(self, request: AgentRequest) -> AgentResult:
        started_at = self._run_logger.start(request)
        with self._lock:
            result = self._run_locked(request)
        self._run_logger.end(request, started_at, result)
        return result

    def _run_locked(self, request: AgentRequest) -> AgentResult:
        try:
            return self._turn(request)
        except FileNotFoundError:
            return self._mapper.failure(request, "missing binary for codex mcp backend", "failed")
        except TimeoutError:
            self._reset_client()
            return self._mapper.failure(request, "Codex MCP timed out", "timeout")
        except RuntimeError as error:
            self._drop_client_if_dead()
            return self._mapper.failure(request, str(error)[:300], "failed")

    def _turn(self, request: AgentRequest) -> AgentResult:
        if not request.session_id:
            return self._attempt(request, "")
        try:
            return self._attempt(request, request.session_id)
        except RuntimeError:
            # Stale threadId or a restarted server: recover on a fresh thread.
            self._drop_client_if_dead()
            return self._attempt(request, "")

    def _attempt(self, request: AgentRequest, thread_id: str) -> AgentResult:
        prompt = self._prompt_builder.build(request)
        tool, arguments = self._call_builder.build(prompt, request.working_directory, thread_id)
        payload = self._client_or_spawn().call_tool(tool, arguments)
        self._run_logger.schema(request, "structuredContent" in payload, "structured_content")
        return self._mapper.success(request, payload)

    def _client_or_spawn(self) -> Client:
        if self._client is None:
            self._client = Client(self._command(), self._server_cwd(), self._timeout())
        return self._client

    def _drop_client_if_dead(self) -> None:
        if self._client is not None and not self._client.is_running():
            self._reset_client()

    def _reset_client(self) -> None:
        client, self._client = self._client, None
        try:
            if client is not None:
                client.stop()
        except OSError:
            pass

    def _command(self) -> list[str]:
        return [self._config.codex_exec_binary.strip() or "codex", "mcp-server"]

    def _server_cwd(self) -> str:
        return self._config.codex_exec_workdir.strip() or "."

    def _timeout(self) -> float:
        return float(self._config.codex_exec_timeout_seconds)
