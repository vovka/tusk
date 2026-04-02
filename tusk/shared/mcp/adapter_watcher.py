try:
    from watchdog.events import FileSystemEventHandler
except ImportError:  # pragma: no cover
    FileSystemEventHandler = object

__all__ = ["AdapterWatcher"]


class AdapterWatcher(FileSystemEventHandler):
    def __init__(self, manager: object) -> None:
        self._manager = manager

    def on_created(self, event) -> None:
        if event.is_directory:
            self._manager.run_async(self._manager.start_adapter(event.src_path))
