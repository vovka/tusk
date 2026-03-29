from dataclasses import dataclass, field

from tusk.lib.llm.interfaces.llm_provider import LLMProvider

__all__ = ["AgentProfile"]


@dataclass(frozen=True)
class AgentProfile:
    profile_id: str
    llm_provider: LLMProvider
    system_prompt: str
    static_tool_names: tuple[str, ...] = field(default_factory=tuple)
    runtime_allowed_tool_names: tuple[str, ...] = field(default_factory=tuple)
    max_steps: int = 16
