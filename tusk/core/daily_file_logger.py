import datetime
import json
import os
import sys

from tusk.interfaces.conversation_logger import ConversationLogger
from tusk.schemas.chat_message import ChatMessage

__all__ = ["DailyFileLogger"]


class DailyFileLogger(ConversationLogger):
    def __init__(self, log_directory: str) -> None:
        self._log_directory = log_directory

    def log_message(self, message: ChatMessage) -> None:
        try:
            self._ensure_directory()
            line = _build_line(message)
            _write_line(self._file_path(), line)
        except OSError as exc:
            print(f"DailyFileLogger: {exc}", file=sys.stderr)

    def _file_path(self) -> str:
        today = datetime.date.today().isoformat()
        return os.path.join(self._log_directory, f"{today}.jsonl")

    def _ensure_directory(self) -> None:
        os.makedirs(self._log_directory, exist_ok=True)


def _build_line(message: ChatMessage) -> str:
    record = {
        "timestamp": datetime.datetime.now().isoformat(timespec="milliseconds"),
        "role": message.role,
        "content": message.content,
    }
    return json.dumps(record)


def _write_line(path: str, line: str) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
