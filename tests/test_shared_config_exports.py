import tusk.shared.config as config


def test_shared_config_exports_present() -> None:
    assert "Config" in config.__all__
    assert "ConfigFactory" in config.__all__
    assert "StartupOptions" in config.__all__
