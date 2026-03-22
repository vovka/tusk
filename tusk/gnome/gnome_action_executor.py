import socket
import subprocess

from tusk.interfaces.action_executor import ActionExecutor
from tusk.schemas.semantic_action import CloseWindowAction, LaunchApplicationAction, SemanticAction, UnrecognizedAction

__all__ = ["GnomeActionExecutor"]

_SOCKET_PATH = "/tmp/tusk/launch.sock"


class GnomeActionExecutor(ActionExecutor):
    def execute(self, action: SemanticAction) -> None:
        if isinstance(action, LaunchApplicationAction):
            self._launch(action)
        elif isinstance(action, CloseWindowAction):
            self._close(action)
        elif isinstance(action, UnrecognizedAction):
            print(f"[EXEC] unrecognized: {action.reason}")
        else:
            raise ValueError(f"Unsupported action type: {type(action)}")

    def _launch(self, action: LaunchApplicationAction) -> None:
        try:
            response = self._send_launch(action.application_name)
            if response.startswith("ok"):
                print(f"[EXEC] launched: {action.application_name}")
            else:
                print(f"[EXEC] launch failed: {response.strip()}")
        except Exception as e:
            print(f"[EXEC] launch failed: {e}")

    def _send_launch(self, exec_cmd: str) -> str:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(_SOCKET_PATH)
            sock.sendall(exec_cmd.encode("utf-8"))
            return sock.recv(256).decode("utf-8")

    def _close(self, action: CloseWindowAction) -> None:
        subprocess.run(
            ["wmctrl", "-c", action.window_title],
            check=False,
        )
