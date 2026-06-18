from tusk.kernel.agent_backends.agent_request import AgentRequest
from tusk.kernel.agent_backends.codex_prompt_builder import CodexPromptBuilder


def test_codex_prompt_builder_includes_request_fields() -> None:
    prompt = CodexPromptBuilder().build(_full_request())

    assert "summarize this file" in prompt
    assert "agent" in prompt
    assert "read_file: Read a file" in prompt
    assert "write_file: Write a file" in prompt
    assert "/workspace/tusk" in prompt
    assert "Never delete user data." in prompt
    assert "Return JSON with status and reply." in prompt


def test_codex_prompt_builder_skips_empty_request_fields() -> None:
    request = AgentRequest("say hi", "agent", context={"available_tools": [None, ""]})

    prompt = CodexPromptBuilder().build(request)

    assert prompt == "## User command\nsay hi\n\n## Mode\nagent"


def _full_request() -> AgentRequest:
    return AgentRequest(
        "summarize this file",
        "agent",
        context=_full_context(),
        working_directory="/workspace/tusk",
    )


def _full_context() -> dict[str, object]:
    return {
        "system_context": "You are running inside TUSK.",
        "available_tools": ["read_file: Read a file", "write_file: Write a file"],
        "safety_policy": "Never delete user data.",
        "response_schema_instruction": "Return JSON with status and reply.",
    }
