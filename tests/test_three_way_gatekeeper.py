import json
from types import SimpleNamespace

from tusk.gnome.gnome_gatekeeper import GnomeGatekeeper
from tusk.schemas.utterance import Utterance


def _gatekeeper() -> GnomeGatekeeper:
    llm = SimpleNamespace(label="test", complete=lambda *a: "")
    return GnomeGatekeeper(llm, SimpleNamespace(log=lambda *a: None))


def _make_response(classification: str, cleaned: str = "", reason: str = "") -> str:
    return json.dumps({"classification": classification, "cleaned_text": cleaned, "reason": reason})


def test_command_is_directed() -> None:
    gk = _gatekeeper()
    gk._llm.complete = lambda *a: _make_response("command", "open Firefox")
    result = gk.evaluate(Utterance("Tusk, open Firefox", b"", 1.0), "prompt")
    assert result.is_directed_at_tusk
    assert result.cleaned_command == "open Firefox"


def test_conversation_is_directed() -> None:
    gk = _gatekeeper()
    gk._llm.complete = lambda *a: _make_response("conversation", "what do you think about Python?")
    result = gk.evaluate(Utterance("Tusk, what do you think?", b"", 1.0), "prompt")
    assert result.is_directed_at_tusk


def test_ambient_is_not_directed() -> None:
    gk = _gatekeeper()
    gk._llm.complete = lambda *a: _make_response("ambient", "", "background noise")
    result = gk.evaluate(Utterance("So I told Sarah", b"", 1.0), "prompt")
    assert not result.is_directed_at_tusk


def test_classification_in_metadata() -> None:
    gk = _gatekeeper()
    gk._llm.complete = lambda *a: _make_response("command", "open Firefox")
    result = gk.evaluate(Utterance("open Firefox", b"", 1.0), "prompt")
    assert result.metadata.get("classification") == "command"


def test_ambient_classification_in_metadata() -> None:
    gk = _gatekeeper()
    gk._llm.complete = lambda *a: _make_response("ambient")
    result = gk.evaluate(Utterance("Thank you", b"", 1.0), "prompt")
    assert result.metadata.get("classification") == "ambient"
