from pathlib import Path


class FileGuardrails:
    def violations(self) -> list[str]:
        return [*self._size_violations(), *self._class_violations()]

    def _size_violations(self) -> list[str]:
        return [f"{path}: {size} code lines" for path, size in self._files() if size > 100]

    def _class_violations(self) -> list[str]:
        return [f"{path}: {count} classes" for path, count in self._class_counts() if count > 1]

    def _files(self) -> list[tuple[str, int]]:
        return [(str(path), self._code_lines(path)) for path in self._python_files()]

    def _python_files(self) -> list[Path]:
        return sorted(Path(".").rglob("*.py"))

    def _code_lines(self, path: Path) -> int:
        return len([line for line in path.read_text().splitlines() if self._is_code(line)])

    def _is_code(self, line: str) -> bool:
        stripped = line.strip()
        return bool(stripped) and not stripped.startswith("#")

    def _class_counts(self) -> list[tuple[str, int]]:
        return [(str(path), path.read_text().count("\nclass ")) for path in self._python_files()]
