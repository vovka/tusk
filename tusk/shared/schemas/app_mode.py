from enum import Enum

__all__ = ["AppMode", "MODE_BYPASS_KIND_PREFIX"]

# A submit kind with this prefix is a wake-word command spoken during dictation/coding: it skips the mode.
MODE_BYPASS_KIND_PREFIX = "mode-bypass:"


class AppMode(Enum):
    DEFAULT = "default"
    DICTATION = "dictation"
    CODING = "coding"
