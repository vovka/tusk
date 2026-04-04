import tempfile
from unittest.mock import patch

from tusk.shared.config import StartupOptions
from tusk.shared.config.startup_options import build_parser
from tusk.shared.logging import ColorLogPrinter, DailyFileLogger
from tusk.shared.schemas.chat_message import ChatMessage


def test_startup_options_expand_groups_and_preview_config() -> None:
    cli = StartupOptions.from_sources(["--show-logs", "stt,llm-with-payload,wait"], {})
    env = StartupOptions.from_sources([], {"SHOW_LOGS": "gate", "LLM_LOG_PREVIEW_CHARS": "140"})
    help_text = "".join(build_parser().format_help().split())
    assert cli.log_groups == frozenset({"transcriber", "llm-request", "llm-payload", "llm-tools", "llm-response", "llm-wait"})
    assert env.log_groups == frozenset({"gatekeeper", "gate-recovery"})
    assert env.llm_log_preview_chars == 140
    assert "llm-payload-full" in help_text


def test_startup_options_support_exclusions() -> None:
    options = StartupOptions.from_sources(["--show-logs", "all,-buffer", "--llm-log-preview-chars", "240"], {})
    assert "buffer" not in options.log_groups
    assert "buffer" in options.hidden_groups
    assert "llm-payload-full" not in options.log_groups
    assert options.llm_log_preview_chars == 240


def test_color_log_printer_honors_hidden_groups_except_error() -> None:
    printer = ColorLogPrinter(frozenset(), frozenset({"ready", "tusk", "error"}))
    with patch("builtins.print") as mocked:
        printer.log("READY", "ready")
        printer.log("TUSK", "spoken")
        printer.log("ERROR", "boom")
    assert mocked.call_count == 1


def test_sanitizer_logs_use_standard_blue_short_label() -> None:
    with patch("builtins.print") as mocked:
        ColorLogPrinter(frozenset({"sanitizer"})).log("SANITIZER", "passed", "sanitizer")
    assert "\033[34m[SANITZR]\033[0m" in mocked.call_args[0][0]


def test_dialog_content_uses_bold_style() -> None:
    with patch("builtins.print") as mocked:
        printer = ColorLogPrinter()
        printer.log("KERNELINPUT", "text='hello'", "kernel-input")
        printer.log("TUSK", "hi there")
    assert "\033[1mtext='hello'\033[0m" in mocked.call_args_list[0].args[0]
    assert "\033[1mhi there\033[0m" in mocked.call_args_list[1].args[0]


def test_diagnostic_content_uses_gray_style() -> None:
    with patch("builtins.print") as mocked:
        ColorLogPrinter(frozenset({"llm-request"})).log("LLMREQUEST", "diagnostic", "llm-request")
    assert "\033[90mdiagnostic\033[0m" in mocked.call_args[0][0]


def test_daily_file_logger_writes_jsonl() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        logger = DailyFileLogger(tmp)
        logger.log_message(ChatMessage("user", "open Firefox"))
        files = list(__import__("pathlib").Path(tmp).glob("*.jsonl"))
        assert len(files) == 1
        assert '"role": "user"' in files[0].read_text()
