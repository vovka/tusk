from dataclasses import dataclass
from typing import Literal, Union

__all__ = ["LaunchApplicationAction", "CloseWindowAction", "SemanticAction"]


@dataclass(frozen=True)
class LaunchApplicationAction:
    action_type: Literal["launch_application"]
    application_name: str


@dataclass(frozen=True)
class CloseWindowAction:
    action_type: Literal["close_window"]
    window_title: str


SemanticAction = Union[LaunchApplicationAction, CloseWindowAction]
