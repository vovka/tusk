#!/usr/bin/env sh
set -eu
SVG="${1:-architecture-deep-zoom.svg}"
OUT="${2:-docs/architecture-deep-zoom/previews}"
mkdir -p "$OUT"
command -v inkscape >/dev/null 2>&1 || { echo "inkscape is required" >&2; exit 1; }
render() {
  name="$1"; area="$2"; width="$3"
  inkscape "$SVG" --export-area="$area" --export-width="$width" \
    --export-filename="$OUT/architecture-preview-$name.png"
}
render overview '0:0:7200:4400' 1800
render system '800:180:6200:4230' 2200
render adapters '4680:470:6110:2920' 2600
render class '4800:600:5950:1430' 2600
render level5 '1210:1110:2200:2290' 2600
