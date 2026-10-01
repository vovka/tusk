#!/usr/bin/env bash
# End-to-end check of the GNOME adapter's Wayland backend against a throwaway headless
# GNOME Shell on a private session bus; the user's own session is never touched.
# Evidence (tool-call log, screenshots, shell log) goes to docs/features/wayland-e2e/.
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
if [ -z "${TUSK_E2E_INNER:-}" ]; then
    exec env -i PATH="$PATH" TUSK_E2E_INNER=1 IMAGE="${IMAGE:-tusk-tusk:latest}" bash "$0"
fi

out="$repo/docs/features/wayland-e2e"
work="$(mktemp -d)"
mkdir -p "$work/home" "$work/run" "$work/data/gnome-shell/extensions" "$out"
chmod 700 "$work/run"
cp -r "$repo/adapters/gnome/shell_extension/tusk-shell@tusk" "$work/data/gnome-shell/extensions/"
export HOME="$work/home" XDG_RUNTIME_DIR="$work/run" XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/home/.config"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$work/run/bus"

bus_pid="$(dbus-daemon --session --address="$DBUS_SESSION_BUS_ADDRESS" --fork --print-pid)"
trap 'kill $(jobs -p) 2>/dev/null; kill "$bus_pid"; sleep 1; fusermount -u "$work/run/doc" 2>/dev/null; rm -rf "$work" 2>/dev/null || true' EXIT
gsettings set org.gnome.shell enabled-extensions "['tusk-shell@tusk']"
gsettings set org.gnome.shell disable-user-extensions false
gnome-shell --headless --virtual-monitor 1280x800 --wayland > "$out/shell.log" 2>&1 &
for _ in $(seq 1 30); do
    gdbus call --session --dest org.tusk.Shell --object-path /org/tusk/Shell \
        --method org.tusk.Shell.ListWindows > /dev/null 2>&1 && break
    sleep 1
done

# The host launcher socket would start apps on the real desktop, so gedit is spawned here.
WAYLAND_DISPLAY=wayland-0 gedit > /dev/null 2>&1 &
sleep 4

docker run --rm --security-opt apparmor=unconfined -u "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONPATH="$repo:/usr/lib/python3/dist-packages" -e XDG_SESSION_TYPE=wayland -e WAYLAND_DISPLAY=wayland-0 \
    -e XDG_RUNTIME_DIR=/run/user/1000 -e DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
    -v "$work/run:/run/user/1000" -v "$work:$work" -v "$repo:$repo" -w "$repo" --entrypoint "" \
    "$IMAGE" python scripts/wayland_e2e_driver.py "$out" "$work"
