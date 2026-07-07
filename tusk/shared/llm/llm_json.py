import json

__all__ = ["extract_json_payload"]


def extract_json_payload(raw: str) -> dict[str, object]:
    """Dict out of an LLM reply: tolerates prose, code fences, list and arguments wrappers."""
    return _unwrapped(_loaded(raw.strip()))


def _loaded(text: str) -> dict | list:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return _first_json_object(text)


def _first_json_object(text: str) -> dict:
    start = text.find("{")
    while start >= 0:
        try:
            value, _ = json.JSONDecoder().raw_decode(text[start:])
            return value
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
    raise ValueError(f"no JSON object in LLM response: {text[:80]!r}")


def _unwrapped(data: dict | list) -> dict[str, object]:
    item = data[0] if isinstance(data, list) and data else data
    if not isinstance(item, dict):
        raise ValueError("LLM response is not a JSON object")
    return item["arguments"] if "arguments" in item else item
