from tusk.kernel.providers.groq_llm import _tool_or_done as groq_tool_or_done
from tusk.kernel.providers.open_router_llm import _tool_or_done as openrouter_tool_or_done


def test_groq_tool_fallback_converts_text_to_done() -> None:
    result = groq_tool_or_done(_response("The text has been entered."))
    assert result.tool_name == "done"


def test_openrouter_tool_fallback_converts_text_to_done() -> None:
    result = openrouter_tool_or_done(_response("Finished."))
    assert result.parameters["reply"] == "Finished."


def _response(text: str) -> object:
    message = type("Message", (), {"tool_calls": [], "content": text})()
    choice = type("Choice", (), {"message": message})()
    return type("Response", (), {"choices": [choice]})()
