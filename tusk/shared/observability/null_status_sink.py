from tusk.shared.interfaces.status_sink import StatusSink
from tusk.shared.schemas.status_snapshot import StatusSnapshot

__all__ = ["NullStatusSink"]


class NullStatusSink(StatusSink):
    def publish(self, snapshot: StatusSnapshot) -> None:
        return None
