__all__ = ["DescribedToolTracker"]


class DescribedToolTracker:
    def __init__(self) -> None:
        self._names: set[str] = set()

    def remember(self, tool_call: object, result: object) -> None:
        name = str(tool_call.parameters.get("name", "")).strip()
        if tool_call.tool_name == "describe_tool" and result.success and name:
            self._names.add(name)

    def names(self) -> set[str]:
        return set(self._names)
