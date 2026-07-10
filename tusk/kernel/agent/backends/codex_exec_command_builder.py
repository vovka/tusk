import shlex
from pathlib import Path

__all__ = ["CodexExecCommandBuilder"]


class CodexExecCommandBuilder:
    def __init__(self, config: object) -> None:
        self._config = config

    def build(self, prompt: str) -> list[str]:
        command = [self._value("codex_exec_binary"), "exec", "--json"]
        command.extend(["--output-schema", self._schema_path()])
        command.extend(self._optional_flag("--model", "codex_exec_model"))
        command.extend(self._optional_flag("--sandbox", "codex_exec_sandbox_mode"))
        command.extend(self._extra_args())
        command.append(prompt)
        return command

    def _schema_path(self) -> str:
        return str(Path(self._value("codex_exec_output_schema_path")))

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
