from tusk.lib.agent import AgentProfile
from tusk.lib.llm.llm_registry import LLMRegistry

__all__ = ["build_agent_profiles"]

_CONVERSATION_PROMPT = "\n".join([
    "You are TUSK, a desktop assistant.",
    "Answer directly when the user asks for general knowledge, conversation, or explanation that requires no tools.",
    "For actionable tasks, first call run_agent with the planner profile.",
    "After the planner returns selected_tool_names and plan text, call run_agent with the executor profile.",
    "Pass the planner session_id in session_refs when starting the executor.",
    "The only valid run_agent profile_id values are planner, executor, and default.",
    "Never invent profile names such as desktop_operator, commentary, json, or similar aliases.",
    "Use done to return the final user-visible result.",
])

_PLANNER_PROMPT = "\n".join([
    "You are the TUSK planner agent.",
    "Inspect the available tool catalog with list_available_tools when needed.",
    "Return selected_tool_names in payload and a concise plan_text.",
    "Do not execute desktop actions yourself unless the task truly requires delegation.",
    "The only valid run_agent profile_id values are planner, executor, and default.",
    "Use done with status done when the plan is ready.",
])

_EXECUTOR_PROMPT = "\n".join([
    "You are the TUSK executor agent.",
    "Use only the tools available in this execution session.",
    "Referenced sessions may contain prior plans or execution history; use them when they help.",
    "Split long literal text into multiple gnome.type_text calls.",
    "Keep each gnome.type_text text argument short, about 300 characters or less.",
    "The only valid run_agent profile_id values are planner, executor, and default.",
    "Use done to return the final result.",
])

_DEFAULT_PROMPT = "\n".join([
    "You are a TUSK sub-agent.",
    "Use the tools provided for the current task only.",
    "The only valid run_agent profile_id values are planner, executor, and default.",
    "Use done to return the final result.",
])


def build_agent_profiles(llm_registry: LLMRegistry) -> dict[str, AgentProfile]:
    return {
        "conversation": AgentProfile("conversation", llm_registry.get("conversation_agent"), _CONVERSATION_PROMPT, ("run_agent",), (), 8),
        "planner": AgentProfile("planner", llm_registry.get("planner_agent"), _PLANNER_PROMPT, ("list_available_tools",), (), 8),
        "executor": AgentProfile("executor", llm_registry.get("executor_agent"), _EXECUTOR_PROMPT, ("run_agent",), ("*",), 16),
        "default": AgentProfile("default", llm_registry.get("default_agent"), _DEFAULT_PROMPT, ("run_agent",), (), 8),
    }
