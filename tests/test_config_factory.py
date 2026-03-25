from tusk.kernel.config_factory import ConfigFactory


def test_config_factory_uses_strict_schema_default_planner_model(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("PLANNER_LLM", raising=False)
    assert ConfigFactory().build().planner_llm.model == "openai/gpt-oss-20b"


def test_config_factory_reads_planner_slot(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("PLANNER_LLM", "groq/openai/gpt-oss-20b")
    assert ConfigFactory().build().planner_llm.model == "openai/gpt-oss-20b"
