from tusk.shared.config import StartupOptions
from tusk.shared.config.startup_options import build_parser


def test_startup_options_expand_groups_and_preview_config() -> None:
    cli = StartupOptions.from_sources(["--show-logs", "stt,llm-with-payload,wait"], {})
    env = StartupOptions.from_sources([], {"SHOW_LOGS": "gate", "LLM_LOG_PREVIEW_CHARS": "140"})
    help_text = "".join(build_parser().format_help().split())
    assert cli.log_groups == frozenset({"transcriber", "llm-request", "llm-payload", "llm-tools", "llm-response", "llm-wait"})
    assert env.log_groups == frozenset({"gatekeeper", "gate-recovery", "dictation-gate", "coding-gate", "speech-stop"})
    assert env.llm_log_preview_chars == 140
    assert "llm-payload-full" in help_text


def test_echo_filter_drop_log_group_is_selectable() -> None:
    options = StartupOptions.from_sources(["--show-logs", "echo-filter"], {})
    assert "echo-filter" in options.log_groups


def test_show_logs_all_includes_echo_filter_drops() -> None:
    options = StartupOptions.from_sources(["--show-logs", "all"], {})
    assert "echo-filter" in options.log_groups


def test_startup_options_support_exclusions() -> None:
    options = StartupOptions.from_sources(["--show-logs", "all,-buffer", "--llm-log-preview-chars", "240"], {})
    assert "buffer" not in options.log_groups
    assert "buffer" in options.hidden_groups
    assert "llm-payload-full" not in options.log_groups
    assert options.llm_log_preview_chars == 240


def test_mode_gate_groups_are_selectable_and_in_gate_alias() -> None:
    options = StartupOptions.from_sources(["--show-logs", "coding-gate"], {})
    gate = StartupOptions.from_sources(["--show-logs", "gate"], {})
    assert "coding-gate" in options.log_groups
    assert {"dictation-gate", "coding-gate", "speech-stop"} <= gate.log_groups
