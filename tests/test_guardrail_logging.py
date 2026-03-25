import tempfile
import types
from unittest.mock import patch

from tusk.kernel.color_log_printer import ColorLogPrinter
from tusk.kernel.daily_file_logger import DailyFileLogger
from tusk.kernel.llm_proxy import LLMProxy
from tusk.kernel.startup_options import StartupOptions, build_parser
from tusk.kernel.schemas.chat_message import ChatMessage


def test_startup_options_enable_groups_from_cli_or_env() -> None:
    cli = StartupOptions.from_sources(["--show-logs", "stt,llm-with-payload"], {})
    env = StartupOptions.from_sources([], {"SHOW_LOGS": "gate"})
    assert cli.log_groups == frozenset({"stt", "llm", "llm-with-payload"})
    assert env.log_groups == frozenset({"gate"})
    assert "llm-with-payload" in build_parser().format_help()


def test_startup_options_default_to_minimal_logs() -> None:
    assert StartupOptions.from_sources([], {}).log_groups == frozenset()


def test_color_log_printer_is_quiet_without_groups() -> None:
    printer = ColorLogPrinter()
    with patch("builtins.print") as mocked:
        printer.log("STT", "hello")
        printer.log("TUSK", "spoken")
    assert mocked.call_count == 1


def test_llm_proxy_logs_slot_payload() -> None:
    logged = []
    proxy = LLMProxy(
        types.SimpleNamespace(label="groq/model", complete=lambda *a: "x", complete_messages=lambda *a: "y"),
        types.SimpleNamespace(log=lambda *a: logged.append(a), show_wait=lambda *a: None, clear_wait=lambda: None),
        slot_name="agent",
    )
    proxy.complete("sys", "hello")
    payload = "\n".join(message for _, message, *_ in logged)
    assert '"slot": "agent"' in payload
    assert '"role": "system"' in payload


def test_daily_file_logger_writes_jsonl() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        logger = DailyFileLogger(tmp)
        logger.log_message(ChatMessage("user", "open Firefox"))
        files = list(__import__("pathlib").Path(tmp).glob("*.jsonl"))
        assert len(files) == 1
        assert '"role": "user"' in files[0].read_text()
