__all__ = ["CallBuilder"]


class CallBuilder:
    """Builds the (tool_name, arguments) pair for a codex mcp-server turn."""

    def __init__(self, config: object) -> None:
        self._config = config

    def build(self, prompt: str, working_directory: str, thread_id: str) -> tuple[str, dict]:
        if thread_id:
            return "codex-reply", {"prompt": prompt, "threadId": thread_id}
        return "codex", self._new_thread_arguments(prompt, working_directory)

    def _new_thread_arguments(self, prompt: str, working_directory: str) -> dict:
        return {
            "prompt": prompt,
            "approval-policy": "never",
            **self._optional("model", self._value("codex_exec_model")),
            **self._optional("sandbox", self._value("codex_exec_sandbox_mode")),
            **self._optional("cwd", working_directory.strip() or self._value("codex_exec_workdir")),
        }

    def _optional(self, key: str, value: str) -> dict:
        return {key: value} if value else {}

    def _value(self, name: str) -> str:
        return str(getattr(self._config, name, "")).strip()
