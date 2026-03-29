from tusk.lib.agent.agent_profile import AgentProfile

__all__ = ["build_agent_profiles"]

_CONVERSATION_PROMPT = "\n".join([
    "You are TUSK, a desktop assistant.",
    "Answer general knowledge and non-tool conversation directly using done.",
    "Delegate actionable work by calling run_agent with the planner profile first.",
    "After the planner returns, call run_agent with the executor profile,",
    "passing the planner's selected_tool_names and session_id as session_refs.",
    "Use done to finish with the final result.",
])

_PLANNER_PROMPT = "\n".join([
    "You are the TUSK planner agent.",
    "Plan the task but do not execute it.",
    "Select real runtime tool names for the executor.",
    "Return done with payload containing selected_tool_names and plan_text.",
    "Use list_available_tools to inspect available runtime tools.",
])

_EXECUTOR_PROMPT = "\n".join([
    "You are the TUSK executor agent.",
    "Execute the plan using only the runtime tools provided.",
    "Do not invent tool names. Use done when finished.",
])

_DEFAULT_PROMPT = "\n".join([
    "You are a TUSK sub-agent.",
    "Complete the given task using available tools.",
    "Use done when finished.",
])


def build_agent_profiles(llm_registry: object) -> dict[str, AgentProfile]:
    return {
        "conversation": _conversation(llm_registry),
        "planner": _planner(llm_registry),
        "executor": _executor(llm_registry),
        "default": _default(llm_registry),
    }


def _conversation(registry: object) -> AgentProfile:
    return AgentProfile("conversation", registry.get("conversation_agent"), _CONVERSATION_PROMPT, ("run_agent",), (), 8)


def _planner(registry: object) -> AgentProfile:
    return AgentProfile("planner", registry.get("planner_agent"), _PLANNER_PROMPT, ("list_available_tools",), (), 8)


def _executor(registry: object) -> AgentProfile:
    return AgentProfile("executor", registry.get("executor_agent"), _EXECUTOR_PROMPT, ("run_agent",), ("*",), 16)


def _default(registry: object) -> AgentProfile:
    return AgentProfile("default", registry.get("default_agent"), _DEFAULT_PROMPT, ("run_agent",), (), 8)
