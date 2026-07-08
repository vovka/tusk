#!/usr/bin/env python3
"""Host-side launcher — runs as the host user, listens on a Unix socket,
executes launch commands received from the TUSK Docker container."""

import os
import shlex
import socket
import subprocess

_SOCKET_PATH = "/tmp/tusk/launch.sock"
_BACKLOG = 5

# Snap injects these to redirect toolkit/loader lookups into its own tree.
# A host GUI app (e.g. gedit) that inherits them loads /snap libs built
# against a different glibc and dies with a GLIBC_PRIVATE symbol error.
_SNAP_ENV_LEAKS = (
    "LD_LIBRARY_PATH", "LD_PRELOAD", "GTK_PATH", "GTK_EXE_PREFIX",
    "GTK_IM_MODULE", "GTK_IM_MODULE_FILE", "GDK_PIXBUF_MODULE_FILE",
    "GDK_PIXBUF_MODULEDIR", "GIO_MODULE_DIR", "GSETTINGS_SCHEMA_DIR",
    "LOCPATH", "XDG_DATA_HOME",
)


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
    subprocess.Popen(shlex.split(data), env=_host_env())


def _host_env() -> dict:
    env = dict(os.environ)
    for var in _SNAP_ENV_LEAKS:
        env.pop(var, None)
    return env


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


def _listening_socket() -> socket.socket:
    # 0o700: the socket executes commands as this user; the container shares
    # the uid (compose user "1000:1000"), other local users get nothing.
    if os.path.exists(_SOCKET_PATH):
        os.unlink(_SOCKET_PATH)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        _bind_and_listen(sock)
    except OSError:
        sock.close()
        raise
    return sock


def _bind_and_listen(sock: socket.socket) -> None:
    sock.bind(_SOCKET_PATH)
    os.chmod(_SOCKET_PATH, 0o700)
    sock.listen(_BACKLOG)


def main() -> None:
    _prepare_socket_dir()
    with _listening_socket() as sock:
        _serve(sock)


if __name__ == "__main__":
    main()
