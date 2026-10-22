import string

__all__ = ["WAKE_WORDS", "has_wake_word", "starts_with_wake_word"]

# "task" and "dusk" are common STT mishearings of the wake word
WAKE_WORDS = frozenset({"tusk", "task", "dusk", "tosk"})


def has_wake_word(text: str) -> bool:
    words = {part.strip(".,!?") for part in text.casefold().split()}
    return bool(words & WAKE_WORDS)


def starts_with_wake_word(text: str) -> bool:
    tokens = text.split()
    return bool(tokens) and tokens[0].strip(string.punctuation).casefold() in WAKE_WORDS
