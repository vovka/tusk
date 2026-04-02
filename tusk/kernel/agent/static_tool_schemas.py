__all__ = [
    "DEFAULT_DONE",
    "EXECUTE_TOOL_SEQUENCE",
    "LIST_TOOLS",
    "PLANNER_DONE",
    "RUN_AGENT",
]


def _sequence_plan_schema() -> dict[str, object]:
    return {"type": "object", "properties": _sequence_plan_properties(), "required": ["steps"], "additionalProperties": False}


def _sequence_plan_properties() -> dict[str, object]:
    return {"goal": {"type": "string"}, "steps": _sequence_steps_schema()}


def _sequence_steps_schema() -> dict[str, object]:
    return {"type": "array", "items": _sequence_step_schema()}


def _sequence_step_schema() -> dict[str, object]:
    properties = {"id": {"type": "string"}, "tool_name": {"type": "string"}, "args": {"type": "object"}}
    return {"type": "object", "properties": properties, "required": ["id", "tool_name", "args"], "additionalProperties": False}


DEFAULT_DONE: dict[str, object] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["done", "clarify", "unknown", "failed", "need_tools"]},
        "summary": {"type": "string"},
        "text": {"type": "string"},
        "payload": {"type": "object"},
        "artifact_refs": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["status", "summary"],
    "additionalProperties": False,
}

PLANNER_DONE: dict[str, object] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["done", "clarify", "unknown", "failed"]},
        "summary": {"type": "string"},
        "text": {"type": "string"},
        "payload": {
            "type": "object",
            "properties": {
                "selected_tool_names": {"type": "array", "items": {"type": "string"}},
                "execution_mode": {"type": "string", "enum": ["normal", "sequence"]},
                "plan_text": {"type": "string"},
                "planned_steps": _sequence_plan_schema(),
                "sequence_plan": _sequence_plan_schema(),
            },
            "required": ["selected_tool_names", "execution_mode", "planned_steps"],
            "additionalProperties": False,
        },
        "artifact_refs": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["status", "summary"],
    "additionalProperties": False,
}

RUN_AGENT: dict[str, object] = {
    "type": "object",
    "properties": {
        "profile_id": {"type": "string", "enum": ["planner", "executor", "default"]},
        "instruction": {"type": "string"},
        "runtime_tool_names": {"type": "array", "items": {"type": "string"}},
        "session_refs": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["profile_id", "instruction"],
    "additionalProperties": False,
}

LIST_TOOLS: dict[str, object] = {"type": "object", "properties": {}, "additionalProperties": False}
EXECUTE_TOOL_SEQUENCE: dict[str, object] = {"type": "object", "properties": {}, "additionalProperties": False}
