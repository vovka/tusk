import types

from shells.emulator.emulator_shell import EmulatorShell


def test_start_submits_only_spoken_lines_in_order(tmp_path, monkeypatch) -> None:
    transcript = tmp_path / "session.txt"
    transcript.write_text("# header comment\n\nOpen gedit.\nStart coding.\n")
    monkeypatch.setenv("TUSK_TRANSCRIPT", str(transcript))
    monkeypatch.setenv("TUSK_UTTERANCE_PAUSE", "0")
    submitted: list[str] = []
    shell = EmulatorShell(sleep=lambda seconds: None)
    shell.start(lambda text: submitted.append(text) or _reply(text))
    assert submitted == ["Open gedit.", "Start coding."]


def test_start_paces_after_every_utterance(tmp_path, monkeypatch) -> None:
    transcript = tmp_path / "session.txt"
    transcript.write_text("one\ntwo\n")
    monkeypatch.setenv("TUSK_TRANSCRIPT", str(transcript))
    monkeypatch.setenv("TUSK_UTTERANCE_PAUSE", "0.25")
    pauses: list[float] = []
    shell = EmulatorShell(sleep=lambda seconds: pauses.append(seconds))
    shell.start(lambda text: _reply(text))
    assert pauses == [0.25, 0.25]


def _reply(text: str) -> object:
    return types.SimpleNamespace(reply=f"ok: {text}")
