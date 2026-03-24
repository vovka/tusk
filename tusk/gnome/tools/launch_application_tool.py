import socket

from tusk.interfaces.agent_tool import AgentTool
from tusk.schemas.tool_result import ToolResult

__all__ = ["LaunchApplicationTool"]


class LaunchApplicationTool(AgentTool):
    def __init__(self, socket_path: str) -> None:
        self._socket_path = socket_path

    @property
    def name(self) -> str:
        return "launch_application"

    @property
    def description(self) -> str:
        return "Launch a desktop application by exec command"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {"application_name": "<exec_cmd>"}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        exec_cmd = parameters["application_name"]
        response = self._send_launch(exec_cmd)
        return self._build_result(exec_cmd, response)

    def _send_launch(self, exec_cmd: str) -> str:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(self._socket_path)
            sock.sendall(exec_cmd.encode("utf-8"))
            return sock.recv(256).decode("utf-8")

    def _build_result(self, exec_cmd: str, response: str) -> ToolResult:
        if response.startswith("ok"):
            return ToolResult(success=True, message=f"launched: {exec_cmd}")
        return ToolResult(success=False, message=f"launch failed: {response.strip()}")
