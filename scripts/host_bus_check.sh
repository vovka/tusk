#!/usr/bin/env bash
# Read-only probe: can the container reach the REAL host session bus, with and without the
# docker-compose.wayland.yml AppArmor override? Only org.freedesktop.DBus.ListNames is called.
set -uo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
out="$repo/docs/features/wayland-e2e/host_bus_check.log"
probe() {
    docker run --rm "$@" -u 1000:1000 -e DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
        -v /run/user/1000/bus:/run/user/1000/bus --entrypoint "" "${IMAGE:-tusk-tusk:latest}" \
        gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
        --method org.freedesktop.DBus.ListNames 2>&1 | cut -c1-200
}
{
    echo "== default compose (docker-default AppArmor profile) =="
    probe
    echo "== with docker-compose.wayland.yml (apparmor=unconfined) =="
    probe --security-opt apparmor=unconfined
} > "$out"
cat "$out"
