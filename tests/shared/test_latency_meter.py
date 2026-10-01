import types

from tusk.shared.status.latency_meter import LatencyMeter


def _meter(now: list[float], logs: list[tuple], medians: list[int]) -> LatencyMeter:
    log = types.SimpleNamespace(log=lambda *args: logs.append(args))
    reporter = types.SimpleNamespace(set_latency_median_ms=medians.append)
    return LatencyMeter(log, reporter, clock=lambda: now[0])


def test_first_tool_call_logs_latency_since_speech_end() -> None:
    now, logs, medians = [10.0], [], []
    meter = _meter(now, logs, medians)
    meter.mark_speech_end(seconds_ago=0.6)
    now[0] = 11.0
    meter.mark_tool_call()
    assert logs == [("LATENCY", "latency speech_end→first_tool_call: 1600 ms", "latency")]
    assert medians == [1600]


def test_only_first_tool_call_per_utterance_is_measured() -> None:
    now, logs, medians = [0.0], [], []
    meter = _meter(now, logs, medians)
    meter.mark_speech_end()
    now[0] = 1.0
    meter.mark_tool_call()
    meter.mark_tool_call()
    assert len(logs) == 1


def test_tool_call_without_speech_is_ignored() -> None:
    logs, medians = [], []
    _meter([0.0], logs, medians).mark_tool_call()
    assert logs == [] and medians == []


def test_median_rolls_over_recent_utterances() -> None:
    now, logs, medians = [0.0], [], []
    meter = _meter(now, logs, medians)
    for delay in (1.0, 3.0, 2.0):
        now[0] = 100.0
        meter.mark_speech_end()
        now[0] = 100.0 + delay
        meter.mark_tool_call()
    assert medians == [1000, 2000, 2000]
