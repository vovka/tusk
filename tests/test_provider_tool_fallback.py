from tusk.kernel.providers.groq_llm import _tool_or_done as groq_tool_or_done
from tusk.kernel.providers.open_router_llm import _tool_or_done as openrouter_tool_or_done
from tusk.kernel.tool_use_failed_recovery import ToolUseFailedRecovery


def test_groq_tool_fallback_converts_text_to_done() -> None:
    result = groq_tool_or_done(_response("The text has been entered."))
    assert result.tool_name == "done"


def test_openrouter_tool_fallback_converts_text_to_done() -> None:
    result = openrouter_tool_or_done(_response("Finished."))
    assert result.parameters["reply"] == "Finished."


def test_tool_use_failed_recovery_extracts_tool_call() -> None:
    exc = RuntimeError(_tool_use_failed_text())
    result = ToolUseFailedRecovery().recover(exc)
    assert result is not None
    assert result.tool_name == "gnome.type_text"
    assert result.parameters["text"] == "hello"


def _response(text: str) -> object:
    message = type("Message", (), {"tool_calls": [], "content": text})()
    choice = type("Choice", (), {"message": message})()
    return type("Response", (), {"choices": [choice]})()


def _tool_use_failed_text() -> str:
    return (
        "Error code: 400 - {'error': {'message': 'Failed to parse tool call arguments as JSON', "
        "'type': 'invalid_request_error', 'code': 'tool_use_failed', "
        '\'failed_generation\': \'{"name": "gnome.type_text", "arguments": {"text": "hello"}}\'}}'
    )
