import subprocess

from tusk.interfaces.action_executor import ActionExecutor
from tusk.schemas.semantic_action import CloseWindowAction, LaunchApplicationAction, SemanticAction

__all__ = ["GnomeActionExecutor"]


class GnomeActionExecutor(ActionExecutor):
    def execute(self, action: SemanticAction) -> None:
        if isinstance(action, LaunchApplicationAction):
            self._launch(action)
        elif isinstance(action, CloseWindowAction):
            self._close(action)
        else:
            raise ValueError(f"Unsupported action type: {type(action)}")

    def _launch(self, action: LaunchApplicationAction) -> None:
        subprocess.Popen(
            [action.application_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _close(self, action: CloseWindowAction) -> None:
        subprocess.run(
            ["wmctrl", "-c", action.window_title],
            check=False,
        )
