import tusk.shared.logging as logging
import tusk.shared.logging.interfaces as interfaces


def test_shared_logging_exports_present() -> None:
    assert "ColorLogPrinter" in logging.__all__
    assert "LogPrinter" in interfaces.__all__
