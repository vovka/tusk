from pathlib import Path

__all__ = ["DirectoryGuardrails"]

_MAX_FILES_PER_DIRECTORY = 12
_MAX_PACKAGE_DEPTH = 4
_SOURCE_ROOTS = ("tusk", "shells", "adapters", "e2e", "demos", "launcher")


class DirectoryGuardrails:
    def __init__(self, root: Path = Path(".")) -> None:
        self._root = root

    def violations(self) -> list[str]:
        return [*self._size_violations(), *self._depth_violations()]

    def _size_violations(self) -> list[str]:
        counts = [(directory, self._file_count(directory)) for directory in self._directories()]
        return [
            f"{self._relative(directory)}: {count} python files (max {_MAX_FILES_PER_DIRECTORY})"
            for directory, count in counts
            if count > _MAX_FILES_PER_DIRECTORY
        ]

    def _depth_violations(self) -> list[str]:
        return [
            f"{self._relative(directory)}: package depth {self._depth(directory)} (max {_MAX_PACKAGE_DEPTH})"
            for directory in self._directories()
            if self._depth(directory) > _MAX_PACKAGE_DEPTH
        ]

    def _directories(self) -> list[Path]:
        found: set[Path] = set()
        for root_name in _SOURCE_ROOTS:
            base = self._root / root_name
            if base.is_dir():
                found.update(self._package_dirs(base))
        return sorted(found)

    def _package_dirs(self, base: Path) -> set[Path]:
        return {path.parent for path in base.rglob("*.py") if not self._excluded(path)}

    def _excluded(self, path: Path) -> bool:
        parts = path.relative_to(self._root).parts
        return any(part.startswith(".") or part == "__pycache__" for part in parts)

    def _file_count(self, directory: Path) -> int:
        return len([path for path in directory.glob("*.py") if path.name != "__init__.py"])

    def _depth(self, directory: Path) -> int:
        return len(directory.relative_to(self._root).parts)

    def _relative(self, directory: Path) -> str:
        return str(directory.relative_to(self._root))
