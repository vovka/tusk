from tusk.kernel.interfaces.llm_provider import LLMProvider
from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.interfaces.task_planner import TaskPlanner
from tusk.kernel.schemas.task_plan import TaskPlan
from tusk.kernel.task_plan_parser import TaskPlanParser
from tusk.kernel.task_planner_message_builder import TaskPlannerMessageBuilder

__all__ = ["LLMTaskPlanner"]

_PROMPT = "\n".join([
    "You plan TUSK task execution.",
    "Read the task and compact tool catalog.",
    "Return execute when you can choose a minimal sufficient tool subset.",
    "Return clarify when the user must answer a short question before execution.",
    "Return unknown when the task cannot be handled.",
    "Do not include tools that are not needed for the plan.",
    "Use strict JSON only.",
])
_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["execute", "clarify", "unknown"]},
        "user_reply": {"type": "string"},
        "plan_steps": {"type": "array", "items": {"type": "string"}},
        "selected_tools": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    "required": ["status", "user_reply", "plan_steps", "selected_tools", "reason"],
    "additionalProperties": False,
}


class LLMTaskPlanner(TaskPlanner):
    def __init__(self, llm_provider: LLMProvider, log_printer: LogPrinter) -> None:
        self._llm = llm_provider
        self._log = log_printer
        self._builder = TaskPlannerMessageBuilder()
        self._parser = TaskPlanParser()

    def plan(
        self,
        task: str,
        tool_catalog: str,
        previous_plan: TaskPlan | None = None,
        needed_capability: str = "",
    ) -> TaskPlan:
        message = self._builder.build(task, tool_catalog, previous_plan, needed_capability)
        raw = self._raw(message)
        self._log.log("LLM", f"[{self._llm.label}] planner → {raw!r}")
        return self._parser.parse(raw)

    def _raw(self, message: str) -> str:
        try:
            return self._llm.complete_structured(_PROMPT, message, "task_plan", _SCHEMA, 512)
        except Exception as exc:
            return self._fallback(message, exc)

    def _fallback(self, message: str, exc: Exception) -> str:
        self._log.log("PLANNER", f"structured output failed: {exc}")
        if "json_validate_failed" not in str(exc):
            raise
        return self._llm.complete(_fallback_prompt(), message, 512)


def _fallback_prompt() -> str:
    return "\n".join([
        _PROMPT,
        'Return one JSON object with keys "status", "user_reply", "plan_steps", "selected_tools", and "reason".',
    ])
