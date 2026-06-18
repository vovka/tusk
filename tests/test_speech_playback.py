import shells.voice.stages.speech_playback as playback_module
from shells.voice.stages.speech_playback import SpeechPlayback


def test_playback_pipes_wav_bytes_to_paplay(monkeypatch) -> None:
    calls: list[tuple[tuple, dict]] = []
    monkeypatch.setattr(playback_module.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    SpeechPlayback().play(b"WAVDATA")
    assert calls[0][0][0] == ["paplay"]
    assert calls[0][1]["input"] == b"WAVDATA"
