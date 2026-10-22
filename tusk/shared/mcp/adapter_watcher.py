from collections.abc import Callable

try:
    from watchdog.events import FileSystemEventHandler
except ImportError:  # pragma: no cover
    FileSystemEventHandler = object

__all__ = ["AdapterWatcher"]


class AdapterWatcher(FileSystemEventHandler):
    def __init__(self, start_adapter: Callable[[str], None]) -> None:
        self._start_adapter = start_adapter

    def on_created(self, event) -> None:
        if event.is_directory:
            self._start_adapter(event.src_path)
