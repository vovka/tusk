from tusk.providers.tts.text_chunker import TextChunker


def test_tts_chunker_wraps_at_word_boundaries() -> None:
    assert TextChunker(4).split("a bb ccc") == ["a bb", "ccc"]


def test_tts_chunker_keeps_long_words_whole() -> None:
    assert TextChunker(5).split("extraordinary yes") == ["extraordinary", "yes"]


def test_tts_chunker_returns_original_for_empty_text() -> None:
    assert TextChunker(10).split("") == [""]


def test_tts_chunker_collapses_whitespace() -> None:
    assert TextChunker(10).split("a\n\n b") == ["a b"]

