import tempfile
import types
from unittest.mock import patch

from tusk.shared.config import StartupOptions
from tusk.shared.config.startup_options import build_parser
from tusk.shared.llm import LLMProxy
from tusk.shared.logging import ColorLogPrinter, DailyFileLogger
from tusk.shared.schemas.chat_message import ChatMessage


def test_startup_options_enable_groups_from_cli_or_env() -> None:
    cli = StartupOptions.from_sources(["--show-logs", "stt,llm-with-payload,wait"], {})
    env = StartupOptions.from_sources([], {"SHOW_LOGS": "gate"})
    assert cli.log_groups == frozenset({"transcriber", "llm-request", "llm-payload", "llm-wait"})
    assert env.log_groups == frozenset({"gatekeeper", "gate-recovery"})
    assert "llm-payload" in build_parser().format_help()


def test_startup_options_default_to_minimal_logs() -> None:
    assert StartupOptions.from_sources([], {}).log_groups == frozenset()


def test_color_log_printer_is_quiet_without_groups() -> None:
    printer = ColorLogPrinter()
    with patch("builtins.print") as mocked:
        printer.log("STT", "hello")
        printer.log("READY", "ready")
        printer.log("TUSK", "spoken")
    assert mocked.call_count == 2


def test_sanitizer_logs_use_cyan_tag() -> None:
    with patch("builtins.print") as mocked:
        ColorLogPrinter(frozenset({"sanitizer"})).log("SANITIZER", "passed", "sanitizer")
    assert "\033[96m[SANITIZER]\033[0m" in mocked.call_args[0][0]


def test_gate_recovery_logs_have_own_label() -> None:
    with patch("builtins.print") as mocked:
        ColorLogPrinter(frozenset({"gate-recovery"})).log("GATERECOVERY", "recovered u1", "gate-recovery")
    assert "\033[96m[GATERECOVERY]\033[0m" in mocked.call_args[0][0]


def test_llm_proxy_logs_request_payload_and_wait_separately() -> None:
    logged = []
    proxy = _proxy(logged)
    proxy.complete("sys", "hello")
    messages = [item for item in logged if item[0] == "log"]
    assert ("wait", "groq/model", "llm-wait") in logged
    assert _has_request(messages)
    assert _has_payload(messages)
    assert '"slot": "agent"' in _payload(messages)
    assert '"role": "system"' in _payload(messages)


def test_daily_file_logger_writes_jsonl() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        logger = DailyFileLogger(tmp)
        logger.log_message(ChatMessage("user", "open Firefox"))
        files = list(__import__("pathlib").Path(tmp).glob("*.jsonl"))
        assert len(files) == 1
        assert '"role": "user"' in files[0].read_text()


def _proxy_log(logged: list[tuple]) -> object:
    return types.SimpleNamespace(
        log=lambda *a: logged.append(("log", *a)),
        show_wait=lambda *a: logged.append(("wait", *a)),
        clear_wait=lambda: logged.append(("clear",)),
    )


def _proxy(logged: list[tuple]) -> LLMProxy:
    llm = types.SimpleNamespace(label="groq/model", complete=lambda *a: "x", complete_messages=lambda *a: "y")
    return LLMProxy(llm, _proxy_log(logged), slot_name="agent")


def _has_request(messages: list[tuple]) -> bool:
    target = ("log", "LLMREQUEST", "[agent] provider=groq/model kind=complete", "llm-request")
    return any(item[:4] == target for item in messages)


def _has_payload(messages: list[tuple]) -> bool:
    return any(item[1] == "LLMPAYLOAD" and item[3] == "llm-payload" for item in messages)


def _payload(messages: list[tuple]) -> str:
    return "\n".join(message for _, _, message, *_ in messages)
