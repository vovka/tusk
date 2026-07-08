from dataclasses import dataclass

from shells.voice.gate_action import GateAction

__all__ = ["GateDispatch"]


@dataclass(frozen=True)
class GateDispatch:
    action: GateAction
    text: str | None = None
    recovered_id: str = ""
    intent: str = ""
