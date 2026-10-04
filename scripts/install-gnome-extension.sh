#!/usr/bin/env bash
# Installs the tusk-shell GNOME Shell extension (window control + virtual input on Wayland).
set -euo pipefail

uuid="tusk-shell@tusk"
source_dir="$(cd "$(dirname "$0")/.." && pwd)/adapters/gnome/shell_extension/$uuid"
target_root="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions"

mkdir -p "$target_root"
ln -sfn "$source_dir" "$target_root/$uuid"
echo "Linked $target_root/$uuid -> $source_dir"

if gnome-extensions enable "$uuid" 2>/dev/null; then
    echo "Enabled $uuid."
else
    echo "GNOME Shell has not seen the extension yet; run 'gnome-extensions enable $uuid' after logging back in."
fi
echo "On Wayland, GNOME Shell only loads new extensions after you log out and log back in."
