import ast
from pathlib import Path


class FunctionGuardrails:
    def violations(self) -> list[str]:
        return [self._format(item) for item in self._oversized_functions()]

    def _oversized_functions(self) -> list[tuple[str, int, str, int]]:
        violations: list[tuple[str, int, str, int]] = []
        for path in sorted(Path(".").rglob("*.py")):
            violations.extend(self._functions_in(path))
        return violations

    def _functions_in(self, path: Path) -> list[tuple[str, int, str, int]]:
        tree = ast.parse(path.read_text())
        return [self._violation(path, node) for node in ast.walk(tree) if self._is_oversized(node)]

    def _is_oversized(self, node: ast.AST) -> bool:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        return self._size(node) > 10

    def _violation(self, path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, int, str, int]:
        size = self._size(node)
        return str(path), node.lineno, node.name, size

    def _format(self, item: tuple[str, int, str, int]) -> str:
        path, line, name, size = item
        return f"{path}:{line} {name} has {size} lines"

    def _size(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        if not node.body:
            return 0
        start = node.body[0].lineno
        end = node.end_lineno or start
        return end - start + 1
