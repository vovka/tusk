import json
from unittest.mock import patch

from tusk.providers.tts import OpenAICompatibleTTS

_URL = "http://localhost:8880/v1/audio/speech"


def test_posts_openai_speech_payload_and_yields_wav() -> None:
    requests: list[object] = []
    with patch("tusk.providers.tts.openai_compatible_tts.urlopen", _fake_urlopen(requests)):
        clips = list(OpenAICompatibleTTS(_URL, "kokoro", "am_michael").synthesize_chunks("hello there"))
    assert clips == [b"WAV"]
    assert requests[0].full_url == _URL
    assert requests[0].get_header("Content-type") == "application/json"
    assert json.loads(requests[0].data) == {
        "model": "kokoro", "input": "hello there", "voice": "am_michael", "response_format": "wav",
    }


def test_synthesizes_lazily_one_request_per_chunk() -> None:
    requests: list[object] = []
    with patch("tusk.providers.tts.openai_compatible_tts.urlopen", _fake_urlopen(requests)):
        chunks = OpenAICompatibleTTS(_URL, "kokoro", "am_michael").synthesize_chunks("word " * 100)
        next(chunks)
        assert len(requests) == 1
        assert len(list(chunks)) >= 1
    assert all(len(json.loads(request.data)["input"]) <= 200 for request in requests)


class _Response:
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return b"WAV"


def _fake_urlopen(requests: list[object]) -> object:
    def urlopen(request: object, timeout: float) -> _Response:
        requests.append(request)
        return _Response()

    return urlopen
