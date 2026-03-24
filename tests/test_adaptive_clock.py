from tusk.core.adaptive_interaction_clock import AdaptiveInteractionClock


def _make_clock(monkeypatch, times, base=30.0, max_t=120.0):
    it = iter(times)
    monkeypatch.setattr("time.monotonic", lambda: next(it))
    return AdaptiveInteractionClock(base, max_t)


def test_no_interactions_not_in_window(monkeypatch) -> None:
    # seconds_since returns inf, _effective_timeout consumes 1
    clock = _make_clock(monkeypatch, [100.0])
    assert not clock.is_within_follow_up_window()


def test_single_recent_interaction(monkeypatch) -> None:
    # record: 1 call, is_within: 2 calls (seconds_since + effective)
    clock = _make_clock(monkeypatch, [100.0, 110.0, 110.0])
    clock.record_interaction()
    assert clock.is_within_follow_up_window()


def test_single_expired_interaction(monkeypatch) -> None:
    clock = _make_clock(monkeypatch, [100.0, 140.0, 140.0])
    clock.record_interaction()
    assert not clock.is_within_follow_up_window()


def test_active_conversation_extends_window(monkeypatch) -> None:
    # 4 record_interactions (4 calls), then is_within (2 calls)
    # effective = 30*3 = 90, seconds_since = 210-160 = 50, 50 < 90 → True
    times = [100.0, 120.0, 140.0, 160.0, 210.0, 210.0]
    clock = _make_clock(monkeypatch, times)
    for _ in range(4):
        clock.record_interaction()
    assert clock.is_within_follow_up_window()


def test_active_conversation_eventually_expires(monkeypatch) -> None:
    # effective = 30*3 = 90, seconds_since = 270-160 = 110, 110 > 90 → False
    times = [100.0, 120.0, 140.0, 160.0, 270.0, 270.0]
    clock = _make_clock(monkeypatch, times)
    for _ in range(4):
        clock.record_interaction()
    assert not clock.is_within_follow_up_window()


def test_effective_timeout_capped_at_max(monkeypatch) -> None:
    times = [float(100 + i) for i in range(20)]
    clock = _make_clock(monkeypatch, times, base=50.0, max_t=60.0)
    for _ in range(10):
        clock.record_interaction()
    assert clock._effective_timeout() <= 60.0


def test_old_interactions_pruned(monkeypatch) -> None:
    # First at 100, second at 500 (400s later, prune removes first)
    times = [100.0, 500.0]
    clock = _make_clock(monkeypatch, times)
    clock.record_interaction()
    clock.record_interaction()
    assert len(clock._interactions) == 1
