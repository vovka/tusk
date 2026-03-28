from tusk.kernel.need_tools_definition import NeedToolsDefinition
from tusk.kernel.terminal_tool_definition_list import TerminalToolDefinitionList

__all__ = ["ExecutionToolDefinitionList"]


class ExecutionToolDefinitionList:
    def __init__(self) -> None:
        self._terminal = TerminalToolDefinitionList()
        self._need_tools = NeedToolsDefinition()

    def build(self, selected: list[dict[str, object]]) -> list[dict[str, object]]:
        return [*self._terminal.build(), self._need_tools.build(), *selected]
