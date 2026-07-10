from tusk.shared.interrupt import InterruptToken


def test_token_starts_uninterrupted() -> None:
    assert not InterruptToken().is_interrupted


def test_interrupt_sets_flag() -> None:
    token = InterruptToken()
    token.interrupt()
    assert token.is_interrupted


def test_clear_resets_flag() -> None:
    token = InterruptToken()
    token.interrupt()
    token.clear()
    assert not token.is_interrupted
