from tusk.shared.fuzzy_name_matcher import FuzzyNameMatcher

_NAMES = ["gedit", "firefox", "gnome-calculator", "Terminal"]


def test_misheard_name_resolves_to_installed_name() -> None:
    assert FuzzyNameMatcher().closest("Jetit", _NAMES) == "gedit"


def test_slightly_misspelled_name_resolves() -> None:
    assert FuzzyNameMatcher().closest("firefix", _NAMES) == "firefox"


def test_unrelated_word_matches_nothing() -> None:
    assert FuzzyNameMatcher().closest("banana", _NAMES) is None
