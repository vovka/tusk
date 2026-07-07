import os
import stat

from launcher import tusk_host_launcher

_SNAP_LEAKS = ("LD_LIBRARY_PATH", "GTK_PATH", "GTK_IM_MODULE_FILE",
               "GIO_MODULE_DIR", "GSETTINGS_SCHEMA_DIR", "LOCPATH")


def test_launch_socket_is_owner_only(monkeypatch, tmp_path):
    path = str(tmp_path / "launch.sock")
    monkeypatch.setattr(tusk_host_launcher, "_SOCKET_PATH", path)
    with tusk_host_launcher._listening_socket():
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o700


def test_host_env_drops_snap_leaks_keeps_rest(monkeypatch):
    for var in _SNAP_LEAKS:
        monkeypatch.setenv(var, "/snap/code/247/leak")
    monkeypatch.setenv("PATH", "/usr/bin")
    env = tusk_host_launcher._host_env()
    assert env["PATH"] == "/usr/bin"
    assert not any(var in env for var in _SNAP_LEAKS)
