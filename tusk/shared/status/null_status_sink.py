from tusk.shared.schemas.status_snapshot import StatusSnapshot
from tusk.shared.status.interfaces.status_sink import StatusSink

__all__ = ["NullStatusSink"]


class NullStatusSink(StatusSink):
    def publish(self, snapshot: StatusSnapshot) -> None:
        return None
