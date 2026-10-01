#!/usr/bin/env bash
# End-to-end check of the GNOME adapter's X11 backend on a throwaway Xvfb :99 with openbox,
# entirely inside a disposable container; the user's display is never used.
# Evidence goes to docs/features/wayland-e2e/x11_*.
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
out="$repo/docs/features/wayland-e2e"
docker run --rm -e PYTHONPATH="$repo:/usr/lib/python3/dist-packages" -e DISPLAY=:99 -e HOME=/tmp \
    -v "$repo:$repo" -w "$repo" --entrypoint "" "${IMAGE:-tusk-tusk:latest}" bash -c "
        apt-get update -qq && apt-get install -y -qq --no-install-recommends xvfb openbox xterm imagemagick > /dev/null
        Xvfb :99 -screen 0 1280x800x24 & sleep 2
        openbox & sleep 1
        xterm -T 'Alpha term' & xterm -T 'Beta term' & sleep 2
        mkdir -p /tmp/work && python scripts/e2e_driver.py x11 '$out' /tmp/work
        chown -R $(id -u):$(id -g) '$out'"
