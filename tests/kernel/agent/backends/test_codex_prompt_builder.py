from tusk.kernel.agent.backends.agent_request import AgentRequest
from tusk.kernel.agent.backends.codex_prompt_builder import CodexPromptBuilder


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

    assert "## Available tools" not in prompt
    assert "## Working directory" not in prompt
    assert "## User command\nsay hi" in prompt
    assert "## Mode\nagent" in prompt


def test_codex_prompt_builder_defaults_system_context_to_desktop_guidance() -> None:
    """Without guidance codex treats commands as terminal tasks (launched gedit
    in its own container shell instead of the gnome MCP tools)."""
    prompt = CodexPromptBuilder().build(AgentRequest("open gedit", "command"))

    assert prompt.startswith("## System context\n")
    assert "gnome MCP tools" in prompt
    assert "launch_application" in prompt
    assert "## User command\nopen gedit" in prompt


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
