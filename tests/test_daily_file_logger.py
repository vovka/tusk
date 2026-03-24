import json
import os

from tusk.core.daily_file_logger import DailyFileLogger
from tusk.schemas.chat_message import ChatMessage


def test_log_message_creates_file(tmp_path) -> None:
    logger = DailyFileLogger(str(tmp_path))
    logger.log_message(ChatMessage("user", "open Firefox"))
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0].name.endswith(".jsonl")


def test_log_message_correct_fields(tmp_path) -> None:
    logger = DailyFileLogger(str(tmp_path))
    logger.log_message(ChatMessage("user", "open Firefox"))
    line = list(tmp_path.iterdir())[0].read_text().strip()
    data = json.loads(line)
    assert data["role"] == "user"
    assert data["content"] == "open Firefox"
    assert "timestamp" in data


def test_two_messages_same_file(tmp_path) -> None:
    logger = DailyFileLogger(str(tmp_path))
    logger.log_message(ChatMessage("user", "open Firefox"))
    logger.log_message(ChatMessage("assistant", "ok"))
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    lines = files[0].read_text().strip().split("\n")
    assert len(lines) == 2


def test_timestamp_is_iso(tmp_path) -> None:
    logger = DailyFileLogger(str(tmp_path))
    logger.log_message(ChatMessage("user", "test"))
    line = list(tmp_path.iterdir())[0].read_text().strip()
    data = json.loads(line)
    assert "T" in data["timestamp"]


def test_creates_directory_if_missing(tmp_path) -> None:
    log_dir = str(tmp_path / "subdir" / "logs")
    logger = DailyFileLogger(log_dir)
    logger.log_message(ChatMessage("user", "test"))
    assert os.path.isdir(log_dir)


def test_io_error_no_exception() -> None:
    logger = DailyFileLogger("/nonexistent/readonly/path")
    logger.log_message(ChatMessage("user", "test"))
