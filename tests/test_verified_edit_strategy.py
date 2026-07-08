import types

from tusk.kernel.modes.edit_strategies.verified_edit_strategy import VerifiedEditStrategy
from tusk.shared.schemas.edit_operation import EditOperation


def test_matching_buffer_skips_fallback() -> None:
    calls: list[str] = []
    strategy = VerifiedEditStrategy(_strategy("primary", calls), _strategy("fallback", calls))
    strategy.apply(EditOperation("insert", 1, 1, "x", "expected"), _driver("expected"))
    assert calls == ["primary"]


def test_drifted_buffer_applies_fallback() -> None:
    calls: list[str] = []
    strategy = VerifiedEditStrategy(_strategy("primary", calls), _strategy("fallback", calls))
    strategy.apply(EditOperation("insert", 1, 1, "x", "expected"), _driver("drifted"))
    assert calls == ["primary", "fallback"]


def test_empty_full_buffer_skips_verification() -> None:
    calls: list[str] = []
    strategy = VerifiedEditStrategy(_strategy("primary", calls), _strategy("fallback", calls))
    strategy.apply(EditOperation("insert", 1, 1, "x", ""), _driver_forbidding_reads())
    assert calls == ["primary"]


def _strategy(name: str, calls: list[str]) -> object:
    return types.SimpleNamespace(apply=lambda edit, driver: calls.append(name))


def _driver(buffer_text: str) -> object:
    return types.SimpleNamespace(read_buffer=lambda: buffer_text)


def _driver_forbidding_reads() -> object:
    def _fail() -> str:
        raise AssertionError("read_buffer must not be called without a full_buffer")

    return types.SimpleNamespace(read_buffer=_fail)
