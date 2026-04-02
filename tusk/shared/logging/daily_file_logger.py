import datetime
import json
from pathlib import Path
import sys

from tusk.shared.logging.interfaces.conversation_logger import ConversationLogger
from tusk.shared.schemas.chat_message import ChatMessage

__all__ = ["DailyFileLogger"]


class DailyFileLogger(ConversationLogger):
    def __init__(self, log_directory: str) -> None:
        self._directory = Path(log_directory)

    def log_message(self, message: ChatMessage) -> None:
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            with self._file_path().open("a", encoding="utf-8") as handle:
                handle.write(_build_line(message) + "\n")
        except OSError as exc:
            print(f"DailyFileLogger: {exc}", file=sys.stderr)

    def _file_path(self) -> Path:
        return self._directory / f"{datetime.date.today().isoformat()}.jsonl"


def _build_line(message: ChatMessage) -> str:
    return json.dumps({
        "timestamp": datetime.datetime.now().isoformat(timespec="milliseconds"),
        "role": message.role,
        "content": message.content,
    })
