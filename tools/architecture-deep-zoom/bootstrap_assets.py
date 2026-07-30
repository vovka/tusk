#!/usr/bin/env python3
"""Extract the generated architecture package from bootstrap chunks."""
from __future__ import annotations
import base64
import io
import tarfile
from pathlib import Path


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parents[1]
    encoded = "".join(path.read_text(encoding="ascii") for path in sorted((script_dir / "bootstrap").glob("part-*.b64")))
    payload = base64.b64decode(encoded)
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        for member in archive.getmembers():
            target = (root / member.name).resolve()
            if root not in target.parents and target != root:
                raise RuntimeError(f"unsafe archive path: {member.name}")
        archive.extractall(root)


if __name__ == "__main__":
    main()
