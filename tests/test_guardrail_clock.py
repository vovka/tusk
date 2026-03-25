from unittest.mock import patch

from tusk.kernel.adaptive_interaction_clock import AdaptiveInteractionClock


def test_active_conversation_extends_window() -> None:
    times = iter([100.0, 120.0, 140.0, 160.0, 210.0, 210.0])
    with patch("time.monotonic", side_effect=lambda: next(times)):
        clock = AdaptiveInteractionClock(30.0, 120.0)
        for _ in range(4):
            clock.record_interaction()
        assert clock.is_within_follow_up_window()


def test_timeout_capped_at_max() -> None:
    times = iter(float(100 + i) for i in range(20))
    with patch("time.monotonic", side_effect=lambda: next(times)):
        clock = AdaptiveInteractionClock(50.0, 60.0)
        for _ in range(10):
            clock.record_interaction()
        assert clock._effective_timeout() <= 60.0
