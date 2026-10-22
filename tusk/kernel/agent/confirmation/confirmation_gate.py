import time
from collections.abc import Callable

from tusk.kernel.agent.confirmation.active_window_probe import ActiveWindowProbe
from tusk.kernel.agent.confirmation.destructive_action_policy import DestructiveActionPolicy
from tusk.kernel.agent.confirmation.pending_action import PendingAction
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.shared.status.latency_meter import LatencyMeter

__all__ = ["ConfirmationGate"]

_CONFIRM_WORDS = {"yes", "confirm", "yes confirm", "do it", "yes do it", "yes please"}
_DECLINE_WORDS = {"no", "cancel", "stop", "no thanks"}


class ConfirmationGate:
    def __init__(self, registry: ToolRegistry, policy: DestructiveActionPolicy | None = None,
                 probe: ActiveWindowProbe | None = None, clock: Callable[[], float] = time.monotonic,
                 ttl_seconds: float = 30.0, latency_meter: LatencyMeter | None = None) -> None:
        self._registry = registry
        self._policy = policy or DestructiveActionPolicy()
        self._probe = probe or ActiveWindowProbe(registry)
        self._clock = clock
        self._ttl_seconds = ttl_seconds
        self._pending: PendingAction | None = None
        self._question: str | None = None
        self._latency_meter = latency_meter

    def execute(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        if self._latency_meter is not None:
            self._latency_meter.mark_tool_call()
        action = self._policy.describe(tool_name, arguments)
        if action is None:
            return self._registry.get(tool_name).execute(arguments)
        return self._hold(tool_name, arguments, action)

    def resolve(self, text: str) -> KernelResponse | None:
        pending, self._pending = self._pending, None
        if pending is None or self._clock() - pending.created_at > self._ttl_seconds:
            return None
        words = " ".join(text.lower().replace(",", " ").replace(".", " ").replace("!", " ").split())
        words = words.removeprefix("tusk ")  # conversation-kind utterances keep the wake word
        if words in _CONFIRM_WORDS:
            return self._confirm(pending)
        return KernelResponse(True, "Cancelled.") if words in _DECLINE_WORDS else None

    def take_question(self) -> str | None:
        question, self._question = self._question, None
        return question

    def _hold(self, tool_name: str, arguments: dict[str, object], action: str) -> ToolResult:
        explicit_target = str(arguments.get("window_title", ""))
        target = explicit_target or self._probe.title()
        if not target:
            return ToolResult(False, f"refused: {action} needs an explicit target window")
        self._pending = PendingAction(tool_name, dict(arguments), target, not explicit_target, self._clock())
        # a bare "yes" is dropped by the voice sanitizer as a likely STT ghost phrase, so ask for the wake word
        self._question = f"{action} '{target}'? Say 'Tusk, yes' to confirm."
        return ToolResult(False, f"needs_confirmation: {self._question} Do not retry; call done.")

    def _confirm(self, pending: PendingAction) -> KernelResponse:
        if pending.follows_active_window and self._probe.title() != pending.target_window:
            return KernelResponse(True, f"Not done: the active window is no longer '{pending.target_window}'.")
        result = self._registry.get(pending.tool_name).execute(pending.arguments)
        return KernelResponse(True, "Done." if result.success else result.message)
