from tusk.shared.interrupt import InterruptToken


def test_interrupt_token_starts_clear() -> None:
    assert InterruptToken().is_interrupted is False


def test_interrupt_token_sets_and_clears() -> None:
    token = InterruptToken()
    token.interrupt()
    assert token.is_interrupted is True
    token.clear()
    assert token.is_interrupted is False
