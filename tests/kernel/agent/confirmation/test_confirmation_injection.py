import types

import pytest

from tusk.kernel.agent.orchestrator_tool_dispatcher import OrchestratorToolDispatcher
from tusk.kernel.agent.tool_sequence.executor import Executor
from tusk.kernel.tools.tool_registry import ToolRegistry


def test_dispatcher_requires_an_injected_confirmation() -> None:
    with pytest.raises(TypeError):
        OrchestratorToolDispatcher(ToolRegistry(), types.SimpleNamespace())


def test_sequence_executor_requires_an_injected_confirmation() -> None:
    with pytest.raises(TypeError):
        Executor(ToolRegistry(), types.SimpleNamespace())
