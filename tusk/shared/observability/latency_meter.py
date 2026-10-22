import statistics
import time
from collections import deque
from collections.abc import Callable

from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.observability.status_reporter import StatusReporter

__all__ = ["LatencyMeter"]


class LatencyMeter:
    """Measures speech end → first tool call per utterance and keeps a rolling median.

    Hot-path impact: two clock reads and one log line per utterance (microseconds).
    """

    def __init__(self, log: LogPrinter, reporter: StatusReporter | None = None,
                 clock: Callable[[], float] = time.monotonic, window: int = 20) -> None:
        self._log = log
        self._reporter = reporter
        self._clock = clock
        self._samples: deque[int] = deque(maxlen=window)
        self._speech_ended_at: float | None = None

    def mark_speech_end(self, seconds_ago: float = 0.0) -> None:
        self._speech_ended_at = self._clock() - seconds_ago

    def mark_tool_call(self) -> None:
        ended_at, self._speech_ended_at = self._speech_ended_at, None
        if ended_at is None:
            return
        elapsed_ms = round((self._clock() - ended_at) * 1000)
        self._log.log("LATENCY", f"latency speech_end→first_tool_call: {elapsed_ms} ms", "latency")
        self._samples.append(elapsed_ms)
        if self._reporter is not None:
            self._reporter.set_latency_median_ms(round(statistics.median(self._samples)))
