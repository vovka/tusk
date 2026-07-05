from pathlib import Path

from adapters.coding import server


def test_repo_root_locates_the_tusk_package() -> None:
    root = Path(server._repo_root())
    assert (root / "tusk").is_dir()


def test_repo_root_is_above_the_adapter_directory() -> None:
    root = Path(server._repo_root())
    assert (root / "adapters" / "coding" / "server.py").exists()
