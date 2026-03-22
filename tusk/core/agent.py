import json

from tusk.interfaces.context_provider import ContextProvider
from tusk.interfaces.llm_provider import LLMProvider
from tusk.schemas.desktop_context import DesktopContext
from tusk.schemas.semantic_action import CloseWindowAction, LaunchApplicationAction, SemanticAction, UnrecognizedAction

__all__ = ["MainAgent"]

_SYSTEM_PROMPT = (
    "You are TUSK, a desktop voice assistant. "
    "Given a user command and desktop context, output ONLY valid JSON matching one of:\n"
    '{"action_type":"launch_application","application_name":"<exec_cmd>"}\n'
    '{"action_type":"close_window","window_title":"<title>"}\n'
    '{"action_type":"unknown","reason":"<why>"}\n'
    "For launch_application, use the exact exec_cmd from the available applications list. "
    "Use the exact window title from context for close_window. "
    "Use unknown if the command is too garbled, nonsensical, or cannot be mapped to a known action. "
    "Respond with JSON only, no explanation."
)


class MainAgent:
    def __init__(self, llm_provider: LLMProvider, context_provider: ContextProvider) -> None:
        self._llm = llm_provider
        self._context = context_provider

    def process_command(self, command: str) -> SemanticAction:
        context = self._context.get_context()
        user_message = self._build_message(command, context)
        raw = self._llm.complete(_SYSTEM_PROMPT, user_message)
        print(f"[LLM:agent] {raw!r}")
        return self._parse_action(raw)

    def _build_message(self, command: str, context: DesktopContext) -> str:
        windows = [w.title for w in context.open_windows]
        apps = "\n".join(f"{a.name} → {a.exec_cmd}" for a in context.available_applications)
        return (
            f"Command: {command}\n"
            f"Active window: {context.active_window_title}\n"
            f"Open windows: {', '.join(windows) or 'none'}\n"
            f"Available apps (name → exec_cmd):\n{apps or 'none'}"
        )

    def _parse_action(self, raw: str) -> SemanticAction:
        data = json.loads(raw.strip())
        action_type = data["action_type"]
        if action_type == "launch_application":
            return LaunchApplicationAction(
                action_type="launch_application",
                application_name=data["application_name"],
            )
        if action_type == "close_window":
            return CloseWindowAction(
                action_type="close_window",
                window_title=data["window_title"],
            )
        if action_type == "unknown":
            return UnrecognizedAction(action_type="unknown", reason=data.get("reason", ""))
        raise ValueError(f"Unknown action_type: {action_type}")
