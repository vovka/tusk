from types import SimpleNamespace

from tusk.providers.llm.tool_response import message_content


def _response(content: object, finish_reason: str = "stop") -> object:
    message = SimpleNamespace(content=content, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish_reason)])


def test_empty_string_completion_names_finish_reason() -> None:
    try:
        message_content(_response("", finish_reason="length"))
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "finish_reason=length" in str(exc)


def test_none_completion_names_finish_reason() -> None:
    try:
        message_content(_response(None, finish_reason="length"))
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "finish_reason=length" in str(exc)
