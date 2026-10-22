from unittest.mock import patch

from tusk.shared.observability import ColorLogPrinter


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
