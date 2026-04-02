import os
import subprocess
import sys
from pathlib import Path

__all__ = ["AdapterEnvironmentBuilder"]


class AdapterEnvironmentBuilder:
    def __init__(self, cache_dir: str) -> None:
        self._cache_dir = Path(cache_dir)

    def build(self, path: Path, manifest: dict) -> dict:
        env = os.environ.copy()
        if not (path / "requirements.txt").exists():
            return env
        cache = self._cache(self._cache_dir, manifest)
        if not self._python_bin(cache).exists():
            self._install(path, cache)
        env["PATH"] = f"{cache / 'bin'}:{env.get('PATH', '')}"
        env["VIRTUAL_ENV"] = str(cache)
        return env

    def _cache(self, root: Path, manifest: dict) -> Path:
        return root / manifest["name"] / manifest["version"]

    def _python_bin(self, cache: Path) -> Path:
        return cache / "bin" / "python"

    def _install(self, path: Path, cache: Path) -> None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(cache)], check=True)
        subprocess.run([str(self._python_bin(cache)), "-m", "pip", "install", "-r", str(path / "requirements.txt")], check=True)
