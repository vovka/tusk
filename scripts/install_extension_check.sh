#!/usr/bin/env bash
# Runs install-gnome-extension.sh with a temporary HOME on a private session bus (no GNOME
# Shell there), so the user's real extensions and session are untouched.
set -uo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
out="$repo/docs/features/wayland-e2e/install_extension_check.log"
home="$(mktemp -d)"
{
    echo "== install with HOME=<tmp> on a private bus =="
    env -i PATH="$PATH" HOME="$home" dbus-run-session -- "$repo/scripts/install-gnome-extension.sh"
    echo "exit=$?"
    echo "== installed entry =="
    ls -l "$home/.local/share/gnome-shell/extensions" | tail -n +2 | sed "s|$home|<tmp>|; s|$repo|<repo>|"
    test -f "$home/.local/share/gnome-shell/extensions/tusk-shell@tusk/metadata.json" && echo "metadata.json reachable"
} > "$out" 2>&1
rm -r "$home"
cat "$out"
