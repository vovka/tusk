from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from tusk.schemas.gate_result import GateResult

if TYPE_CHECKING:
    from tusk.interfaces.pipeline_controller import PipelineController

__all__ = ["PipelineMode"]


class PipelineMode(ABC):
    @property
    @abstractmethod
    def gatekeeper_prompt(self) -> str:
        ...

    @abstractmethod
    def handle_utterance(
        self,
        gate_result: GateResult,
        controller: PipelineController,
    ) -> None:
        ...
