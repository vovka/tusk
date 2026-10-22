from shells.voice.gate.wake_words import has_wake_word, starts_with_wake_word


def test_stt_mishearings_count_as_wake_word() -> None:
    assert has_wake_word("Tosk close it")
    assert has_wake_word("Dusk, open the browser")


def test_starts_with_wake_word_ignores_punctuation_and_case() -> None:
    assert starts_with_wake_word("TOSK, maximize it.")
    assert not starts_with_wake_word("I told tusk about it.")
