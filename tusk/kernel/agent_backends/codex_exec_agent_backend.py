import json
import os
import shlex
import subprocess
import time
from pathlib import Path

from tusk.kernel.agent_backends.agent_backend import AgentBackend
from tusk.kernel.agent_backends.agent_request import AgentRequest
from tusk.kernel.agent_backends.agent_result import AgentResult
from tusk.shared.logging.interfaces.log_printer import LogPrinter

__all__ = ["CodexExecAgentBackend"]


class CodexExecAgentBackend(AgentBackend):
    def __init__(self, config: object, log_printer: LogPrinter) -> None:
        if config is None:
            raise ValueError("config cannot be None")
        if log_printer is None:
            raise ValueError("log_printer cannot be None")
        self._config = config
        self._log_printer = log_printer

    @property
    def name(self) -> str:
        return "codex_exec"

    @property
    def supports_streaming(self) -> bool:
        return False

    def run(self, request: AgentRequest) -> AgentResult:
        if request is None:
            raise ValueError("request cannot be None")
        started_at = time.monotonic()
        return self._run_process(request, started_at)

    def _run_process(self, request: AgentRequest, started_at: float) -> AgentResult:
        try:
            completed = self._execute(request)
        except FileNotFoundError:
            return self._failure(request, "missing binary for codex exec backend", "failed")
        except subprocess.TimeoutExpired:
            return self._failure(request, "Codex exec timed out", "timeout")
        return self._completed(request, completed, started_at)

    def _execute(self, request: AgentRequest) -> subprocess.CompletedProcess:
        request_env = getattr(request, "environment", None) or {}
        return subprocess.run(
            self._command(request.user_text), cwd=self._cwd(request), timeout=self._timeout(request),
            env={**os.environ, **request_env}, capture_output=True, text=True,
        )

    def _command(self, prompt: str) -> list[str]:
        command = [self._value("codex_exec_binary"), "exec", "--json"]
        command.extend(["--output-schema", str(Path(self._value("codex_exec_output_schema_path")))])
        command.extend(self._optional_flag("--model", "codex_exec_model"))
        command.extend(self._optional_flag("--sandbox", "codex_exec_sandbox_mode"))
        command.extend(self._extra_args())
        command.append(prompt)
        return command

    def _completed(
        self, request: AgentRequest, completed: subprocess.CompletedProcess, started_at: float
    ) -> AgentResult:
        self._log_completion(completed, started_at)
        if completed.returncode != 0:
            return self._failure(request, self._exit_message(completed), "failed")
        return self._parsed(request, completed.stdout)

    def _parsed(self, request: AgentRequest, output: str) -> AgentResult:
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            return self._failure(request, "Invalid JSON from codex exec", "failed")
        return self._structured_result(request, parsed)

    def _structured_result(self, request: AgentRequest, parsed: object) -> AgentResult:
        status = self._status(parsed)
        reply = self._reply(parsed)
        return AgentResult(
            status == "success", reply, request.session_id, self._metadata(request), status, reply, parsed
        )

    def _failure(self, request: AgentRequest, message: str, status: str) -> AgentResult:
        return AgentResult(False, message, request.session_id, self._metadata(request), status, message)

    def _metadata(self, request: AgentRequest) -> dict[str, object]:
        return {**request.metadata, "backend": self.name, "mode": request.mode}

    def _status(self, parsed: object) -> str:
        if not isinstance(parsed, dict):
            return "success"
        return str(parsed.get("status", "success"))

    def _reply(self, parsed: object) -> str:
        if not isinstance(parsed, dict):
            return str(parsed)
        return str(parsed.get("reply") or parsed.get("final_text") or "")

    def _cwd(self, request: AgentRequest) -> str | None:
        directory = getattr(request, "working_directory", "") or self._value("codex_exec_workdir")
        return str(Path(directory)) if directory else None

    def _timeout(self, request: AgentRequest) -> object:
        timeout = getattr(request, "timeout_seconds", None)
        if timeout is not None:
            return timeout
        return getattr(self._config, "codex_exec_timeout_seconds")

    def _value(self, name: str) -> str:
        return str(getattr(self._config, name, "")).strip()

    def _optional_flag(self, flag: str, name: str) -> list[str]:
        value = self._value(name)
        return [flag, value] if value else []

    def _extra_args(self) -> list[str]:
        configured = getattr(self._config, "codex_exec_extra_args", None)
        if not configured:
            return []
        return shlex.split(configured) if isinstance(configured, str) else list(configured)

    def _exit_message(self, completed: subprocess.CompletedProcess) -> str:
        summary = str(completed.stderr or "").strip()[:300]
        return f"Codex exec failed with exit code {completed.returncode}: {summary}"

    def _log_completion(self, completed: subprocess.CompletedProcess, started_at: float) -> None:
        elapsed = time.monotonic() - started_at
        message = f"codex exec completed with exit code {completed.returncode} in {elapsed:.2f}s"
        if getattr(self._config, "codex_exec_log_raw_events", False):
            message = f"{message}; stdout={completed.stdout}; stderr={completed.stderr}"
        self._log_printer.log("codex_exec", message, "agent")
