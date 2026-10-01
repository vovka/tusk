import difflib

__all__ = ["FuzzyNameMatcher"]

# Collapses voiced/unvoiced consonant pairs STT confuses, e.g. "Jetit" vs "gedit".
_SOUND_ALIKE = str.maketrans("jtpk", "gdbg")
_MIN_SIMILARITY = 0.8
_MIN_CANDIDATE_SIMILARITY = 0.6


class FuzzyNameMatcher:
    """Finds the installed name that sounds or is spelled most like a possibly misheard name."""

    def closest(self, query: str, names: list[str]) -> str | None:
        keys = {self._key(name): name for name in names}
        found = difflib.get_close_matches(self._key(query), list(keys), n=1, cutoff=_MIN_SIMILARITY)
        return keys[found[0]] if found else None

    def candidates(self, query: str, names: list[str], limit: int) -> list[str]:
        keys = {self._key(name): name for name in names}
        found = difflib.get_close_matches(self._key(query), list(keys), n=limit, cutoff=_MIN_CANDIDATE_SIMILARITY)
        return [keys[key] for key in found]

    def _key(self, name: str) -> str:
        return name.casefold().translate(_SOUND_ALIKE)
