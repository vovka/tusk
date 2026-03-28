#!/usr/bin/env python3
"""Host-side launcher — runs as the host user, listens on a Unix socket,
executes launch commands received from the TUSK Docker container."""

import os
import shlex
import socket
import subprocess

_SOCKET_PATH = "/tmp/tusk/launch.sock"
_BACKLOG = 5


def _handle(conn: socket.socket) -> None:
    with conn:
        data = _read(conn)
        if not data:
            return
        print(f"[launcher] exec: {data!r}")
        try:
            _launch(data)
            _send(conn, "ok\n")
        except Exception as exc:
            _send_error(conn, exc)


def _serve(sock: socket.socket) -> None:
    print(f"[launcher] listening on {_SOCKET_PATH}")
    while True:
        conn, _ = sock.accept()
        _handle(conn)


def _read(conn: socket.socket) -> str:
    return conn.recv(4096).decode("utf-8").strip()


def _launch(data: str) -> None:
    subprocess.Popen(shlex.split(data))


def _send(conn: socket.socket, message: str) -> None:
    conn.sendall(message.encode("utf-8"))


def _send_error(conn: socket.socket, exc: Exception) -> None:
    msg = f"error: {exc}\n"
    print(f"[launcher] {msg.strip()}")
    _send(conn, msg)


def _prepare_socket_dir() -> None:
    dir_path = os.path.dirname(_SOCKET_PATH)
    os.makedirs(dir_path, exist_ok=True)
    if not os.access(dir_path, os.W_OK):
        raise PermissionError(
            f"Cannot write to {dir_path!r}: directory is owned by another user. "
            f"Fix with: sudo rm -rf {dir_path}"
        )


def main() -> None:
    _prepare_socket_dir()
    if os.path.exists(_SOCKET_PATH):
        os.unlink(_SOCKET_PATH)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.bind(_SOCKET_PATH)
        os.chmod(_SOCKET_PATH, 0o777)
        sock.listen(_BACKLOG)
        _serve(sock)


if __name__ == "__main__":
    main()
