import ast
import json
import subprocess

__all__ = ["ShellBus"]

_DESTINATION = ["--dest", "org.tusk.Shell", "--object-path", "/org/tusk/Shell", "--method"]


class ShellBus:
    """Calls the tusk-shell GNOME Shell extension over the session bus via `gdbus`."""

    # Latency: one gdbus process per call (~10 ms); on the input hot path on Wayland.
    def call(self, method: str, arguments: list[object]) -> str:
        # JSON scalars, strings and string lists are valid GVariant text.
        command = ["gdbus", "call", "--session", *_DESTINATION, f"org.tusk.Shell.{method}"]
        result = subprocess.run([*command, *self._gvariant_texts(arguments)], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"tusk-shell {method} failed: {result.stderr.strip()}")
        return result.stdout

    def call_string(self, method: str) -> str:
        # gdbus prints a GVariant tuple such as ('text',), which is a valid Python literal.
        return ast.literal_eval(self.call(method, []).strip())[0]

    def _gvariant_texts(self, arguments: list[object]) -> list[str]:
        # Raw UTF-8 instead of \u escapes: GVariant text rejects JSON's surrogate-pair escapes.
        return [json.dumps(argument, ensure_ascii=False) for argument in arguments]
