#!/usr/bin/env python3
"""Validate and optionally render the standalone deep-zoom architecture SVG."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

SVG_NS = "{http://www.w3.org/2000/svg}"
LEVEL_PATTERN = re.compile(r"\.l([1-5])\s*\{\s*font-size:([0-9.]+)px")
EXTERNAL_URI = re.compile(r"^(?:https?:|//)", re.IGNORECASE)

RENDER_AREAS = {
    "overview": "0:0:7200:4400",
    "system": "800:180:6200:4230",
    "adapters": "4680:470:6110:2920",
    "class": "4800:600:5950:1430",
    "level5": "1210:1110:2200:2290",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def render(svg: Path, output_dir: Path) -> list[dict[str, object]]:
    inkscape = shutil.which("inkscape")
    if not inkscape:
        return [{"status": "skipped", "reason": "inkscape not found"}]
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    for name, area in RENDER_AREAS.items():
        target = output_dir / f"architecture-preview-{name}.png"
        command = [
            inkscape,
            str(svg),
            f"--export-area={area}",
            "--export-width=1800",
            f"--export-filename={target}",
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        results.append(
            {
                "name": name,
                "area": area,
                "output": str(target),
                "status": "passed" if completed.returncode == 0 and target.exists() else "failed",
                "stderr": completed.stderr.strip()[-500:] if completed.returncode != 0 else "",
            }
        )
    return results


def validate(svg: Path, preview_dir: Path | None = None) -> dict[str, object]:
    raw = svg.read_text(encoding="utf-8")
    root = ET.fromstring(raw)
    elements = list(root.iter())
    ids = [value for element in elements if (value := element.attrib.get("id"))]
    counts = Counter(ids)
    duplicates = sorted(item for item, count in counts.items() if count > 1)

    node_groups = [
        element
        for element in elements
        if local_name(element.tag) == "g" and "node" in element.attrib.get("class", "").split()
    ]
    titled_nodes = [element for element in node_groups if element.find(f"{SVG_NS}title") is not None]
    external_references: list[str] = []
    scripts = 0
    images = 0
    for element in elements:
        name = local_name(element.tag)
        scripts += name == "script"
        images += name == "image"
        for key, value in element.attrib.items():
            if key.endswith("href") and EXTERNAL_URI.match(value.strip()):
                external_references.append(value)

    style_text = "\n".join((element.text or "") for element in elements if local_name(element.tag) == "style")
    scales = {int(level): float(size) for level, size in LEVEL_PATTERN.findall(style_text)}
    adjacent_ratios = {
        f"l{level}/l{level + 1}": round(scales[level] / scales[level + 1], 3)
        for level in range(1, 5)
        if level in scales and level + 1 in scales
    }

    preview_results: list[dict[str, object]] = []
    if preview_dir and preview_dir.exists():
        try:
            from PIL import Image
        except ImportError:
            preview_results.append({"status": "skipped", "reason": "Pillow not installed"})
        else:
            for path in sorted(preview_dir.glob("*.png")):
                with Image.open(path) as image:
                    preview_results.append(
                        {
                            "path": str(path),
                            "width": image.width,
                            "height": image.height,
                            "mode": image.mode,
                            "status": "passed" if image.width > 0 and image.height > 0 else "failed",
                        }
                    )

    checks = {
        "well_formed_xml": True,
        "svg_root": local_name(root.tag) == "svg",
        "standalone_no_scripts": scripts == 0,
        "standalone_no_external_images": images == 0,
        "standalone_no_external_hrefs": not external_references,
        "unique_ids": not duplicates,
        "all_architecture_nodes_titled": len(node_groups) == len(titled_nodes),
        "five_text_levels_present": set(scales) == {1, 2, 3, 4, 5},
        "adjacent_scale_ratios_between_4x_and_8x": all(4.0 <= value <= 8.0 for value in adjacent_ratios.values()),
        "viewbox_expected": root.attrib.get("viewBox") == "0 0 7200 4400",
    }
    return {
        "file": str(svg),
        "sha256": sha256(svg),
        "bytes": svg.stat().st_size,
        "checks": checks,
        "passed": all(checks.values()),
        "element_count": len(elements),
        "group_count": sum(local_name(element.tag) == "g" for element in elements),
        "id_count": len(ids),
        "duplicate_ids": duplicates,
        "architecture_node_count": len(node_groups),
        "nodes_with_title": len(titled_nodes),
        "text_level_sizes_px": scales,
        "adjacent_text_scale_ratios": adjacent_ratios,
        "external_references": external_references,
        "included_preview_files": preview_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("svg", nargs="?", default="architecture-deep-zoom.svg")
    parser.add_argument("--preview-dir", default="docs/architecture-deep-zoom/previews")
    parser.add_argument("--render-dir", help="Render five validation views with Inkscape")
    parser.add_argument("--json", dest="json_path", help="Write the report to this JSON file")
    args = parser.parse_args()

    report = validate(Path(args.svg), Path(args.preview_dir) if args.preview_dir else None)
    if args.render_dir:
        report["rendered_views"] = render(Path(args.svg), Path(args.render_dir))
        report["rendering_passed"] = all(item.get("status") in {"passed", "skipped"} for item in report["rendered_views"])
    output = json.dumps(report, indent=2, sort_keys=True)
    print(output)
    if args.json_path:
        target = Path(args.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
