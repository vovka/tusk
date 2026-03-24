from tusk.providers.groq_stt import GroqSTT


def _stt() -> GroqSTT:
    return GroqSTT("fake-key")


def test_blank_audio_is_non_speech() -> None:
    assert _stt()._is_non_speech("[BLANK_AUDIO]")


def test_thank_you_passes_now() -> None:
    assert not _stt()._is_non_speech("thank you")


def test_open_firefox_passes() -> None:
    assert not _stt()._is_non_speech("open Firefox")


def test_empty_is_non_speech() -> None:
    assert _stt()._is_non_speech("")


def test_music_tag_is_non_speech() -> None:
    assert _stt()._is_non_speech("[Music]")
