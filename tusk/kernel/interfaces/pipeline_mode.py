from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from tusk.shared.schemas.gate_result import GateResult
from tusk.shared.schemas.utterance import Utterance

if TYPE_CHECKING:
    from tusk.kernel.interfaces.pipeline_controller import PipelineController

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
        utterance: Utterance,
        controller: PipelineController,
    ) -> None:
        ...
