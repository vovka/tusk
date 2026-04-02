from dataclasses import dataclass

from tusk.shared.llm.interfaces.llm_provider import LLMProvider

__all__ = ["AgentProfile"]


@dataclass(frozen=True)
class AgentProfile:
    profile_id: str
    llm_provider: LLMProvider
    system_prompt: str
    static_tool_names: tuple[str, ...] = ()
    runtime_allowed_tool_names: tuple[str, ...] = ()
    max_steps: int = 16
