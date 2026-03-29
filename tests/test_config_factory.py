from tusk.lib.config import ConfigFactory


def test_config_factory_uses_default_profile_fallbacks(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("CONVERSATION_AGENT_LLM", raising=False)
    monkeypatch.delenv("PLANNER_AGENT_LLM", raising=False)
    monkeypatch.delenv("EXECUTOR_AGENT_LLM", raising=False)
    monkeypatch.delenv("DEFAULT_AGENT_LLM", raising=False)
    config = ConfigFactory().build()
    assert config.conversation_agent_llm.model == "openai/gpt-oss-120b"
    assert config.planner_agent_llm.model == "openai/gpt-oss-20b"
    assert config.executor_agent_llm.model == "openai/gpt-oss-120b"
    assert config.default_agent_llm.model == "openai/gpt-oss-120b"


def test_config_factory_reads_profile_specific_slots(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("CONVERSATION_AGENT_LLM", "groq/openai/gpt-oss-120b")
    monkeypatch.setenv("PLANNER_AGENT_LLM", "groq/openai/gpt-oss-20b")
    monkeypatch.setenv("EXECUTOR_AGENT_LLM", "groq/llama-3.3-70b-versatile")
    monkeypatch.setenv("DEFAULT_AGENT_LLM", "groq/llama-3.1-8b-instant")
    config = ConfigFactory().build()
    assert config.conversation_agent_llm.model == "openai/gpt-oss-120b"
    assert config.planner_agent_llm.model == "openai/gpt-oss-20b"
    assert config.executor_agent_llm.model == "llama-3.3-70b-versatile"
    assert config.default_agent_llm.model == "llama-3.1-8b-instant"
