import ast
from pathlib import Path

__all__ = ["ImportGuardrails"]

_FIRST_PARTY_ROOTS = ("adapters", "demos", "e2e", "launcher", "main", "shell_loader", "shells", "tests", "tools", "tusk")
_ALLOWED_IMPORTS = {
    # adapter servers are standalone process entrypoints, so they compose their own providers
    "adapters": ("adapters", "tusk.shared", "tusk.providers"),
    "shells": ("shells", "tusk.shared"),
    "tusk/kernel": ("tusk.kernel", "tusk.shared"),
    "tusk/providers": ("tusk.providers", "tusk.shared"),
    "tusk/shared": ("tusk.shared",),
}


class ImportGuardrails:
    def __init__(self, root: Path = Path(".")) -> None:
        self._root = root

    def violations(self) -> list[str]:
        found: list[str] = []
        for tree_path, allowed in _ALLOWED_IMPORTS.items():
            found.extend(self._tree_violations(tree_path, allowed))
        return found

    def _tree_violations(self, tree_path: str, allowed: tuple[str, ...]) -> list[str]:
        found: list[str] = []
        for path in self._python_files(self._root / tree_path):
            found.extend(self._file_violations(path, allowed))
        return found

    def _python_files(self, base: Path) -> list[Path]:
        if not base.is_dir():
            return []
        return [path for path in sorted(base.rglob("*.py")) if not self._excluded(path)]

    def _excluded(self, path: Path) -> bool:
        parts = path.relative_to(self._root).parts
        return any(part.startswith(".") or part == "__pycache__" for part in parts)

    def _file_violations(self, path: Path, allowed: tuple[str, ...]) -> list[str]:
        return [
            self._format(path, name, allowed)
            for name in self._imported_modules(path)
            if self._breaks_boundary(name, allowed)
        ]

    def _imported_modules(self, path: Path) -> list[str]:
        names: list[str] = []
        for node in ast.walk(ast.parse(path.read_text())):
            names.extend(self._module_names(node, path))
        return names

    def _module_names(self, node: ast.AST, path: Path) -> list[str]:
        if isinstance(node, ast.Import):
            return [alias.name for alias in node.names]
        if isinstance(node, ast.ImportFrom):
            return [self._absolute_name(node, path)]
        return []

    def _absolute_name(self, node: ast.ImportFrom, path: Path) -> str:
        if node.level == 0:
            return node.module or ""
        package_parts = path.relative_to(self._root).parent.parts
        base = ".".join(package_parts[: len(package_parts) - node.level + 1])
        return f"{base}.{node.module}" if node.module else base

    def _breaks_boundary(self, name: str, allowed: tuple[str, ...]) -> bool:
        if not any(_within(name, root) for root in _FIRST_PARTY_ROOTS):
            return False
        return not any(_within(name, prefix) for prefix in allowed)

    def _format(self, path: Path, name: str, allowed: tuple[str, ...]) -> str:
        return f"{path.relative_to(self._root)}: imports {name} (allowed: {', '.join(allowed)})"


def _within(name: str, prefix: str) -> bool:
    return name == prefix or name.startswith(prefix + ".")
