from types import SimpleNamespace

from tusk.kernel.agent.backends.codex_mcp.call_builder import CallBuilder


def builder(model: str = "", sandbox: str = "", workdir: str = "") -> CallBuilder:
    config = SimpleNamespace(
        codex_exec_model=model, codex_exec_sandbox_mode=sandbox, codex_exec_workdir=workdir
    )
    return CallBuilder(config)


def test_new_thread_uses_codex_tool_with_prompt_and_approval_policy() -> None:
    tool, arguments = builder().build("open gedit", "", "")
    assert tool == "codex"
    assert arguments["prompt"] == "open gedit"
    assert arguments["approval-policy"] == "never"


def test_new_thread_includes_configured_model_sandbox_and_cwd() -> None:
    tool, arguments = builder("gpt-5.5", "workspace-write", "/app").build("hi", "", "")
    assert arguments["model"] == "gpt-5.5"
    assert arguments["sandbox"] == "workspace-write"
    assert arguments["cwd"] == "/app"


def test_new_thread_omits_blank_optional_values() -> None:
    tool, arguments = builder(model=" ", sandbox="", workdir="  ").build("hi", "", "")
    assert set(arguments) == {"prompt", "approval-policy"}


def test_request_working_directory_overrides_configured_workdir() -> None:
    tool, arguments = builder(workdir="/app").build("hi", "/tmp/task", "")
    assert arguments["cwd"] == "/tmp/task"


def test_thread_id_uses_codex_reply_with_exactly_prompt_and_thread_id() -> None:
    tool, arguments = builder("gpt-5.5", "workspace-write", "/app").build("more", "/tmp", "t-42")
    assert tool == "codex-reply"
    assert arguments == {"prompt": "more", "threadId": "t-42"}
