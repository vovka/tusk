from tusk.kernel.config_factory import ConfigFactory


def test_config_factory_reads_tool_usage_file(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("TUSK_TOOL_USAGE_FILE", "runtime/tool-usage.json")
    assert ConfigFactory().build().tool_usage_file == "runtime/tool-usage.json"
