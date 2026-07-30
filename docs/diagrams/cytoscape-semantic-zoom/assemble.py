from __future__ import annotations

import base64
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "payload"


def decode_gzip_b64(parts: list[Path]) -> str:
    encoded = "".join(path.read_text(encoding="ascii") for path in parts)
    return gzip.decompress(base64.b64decode(encoded)).decode("utf-8")


def main() -> None:
    template = decode_gzip_b64([PAYLOAD / "template.gz.b64"])
    app = decode_gzip_b64(sorted(PAYLOAD.glob("app.part-*")))
    cytoscape = (PAYLOAD / "cytoscape.min.js").read_text(encoding="utf-8")

    html = template.replace("{{CYTOSCAPE}}", cytoscape).replace("{{APP}}", app)
    if "{{CYTOSCAPE}}" in html or "{{APP}}" in html:
        raise RuntimeError("unresolved architecture diagram template marker")

    output = ROOT / "tusk-cytoscape-architecture.html"
    output.write_text(html, encoding="utf-8")
    print(f"wrote {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
