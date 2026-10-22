from types import SimpleNamespace

from tusk.shared.mcp import AdapterWatcher


def test_new_directory_starts_adapter_by_path() -> None:
    started: list[str] = []
    AdapterWatcher(started.append).on_created(SimpleNamespace(is_directory=True, src_path="/adapters/new"))
    assert started == ["/adapters/new"]


def test_new_file_is_ignored() -> None:
    started: list[str] = []
    AdapterWatcher(started.append).on_created(SimpleNamespace(is_directory=False, src_path="/adapters/x.json"))
    assert started == []
