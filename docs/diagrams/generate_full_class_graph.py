#!/usr/bin/env python3
"""Wrap a pyreverse classes .dot file into nested per-package subgraph clusters.

Usage: generate_full_class_graph.py <pyreverse_classes.dot> <output.dot>

Render the output with fdp, not dot — dot strings disconnected clusters into a
single line. The embedded legend lives in full-class-graph-legend.gv next to
this script (kept as data so this file stays within the code-size guardrails).
"""
import re
import sys
from pathlib import Path

# (top-level pattern, cluster name, fill color, sub-cluster names).
# A node lands in sub-cluster S when its qualified name contains ".S.".
RULES = [
    (r"^tusk\.kernel\.agent\.backends\.", "kernel.agent.backends", "#fde8e8", ["codex_mcp"]),
    (r"^tusk\.kernel\.agent\.", "kernel.agent", "#f8d9d9",
     ["session", "runtime", "planner", "tool_sequence", "guards"]),
    (r"^tusk\.kernel\.", "kernel.core", "#fbe5c8", ["core", "interfaces", "modes", "tools"]),
    (r"^tusk\.shared\.schemas\.", "shared.schemas", "#e3f2e1", ["tools", "desktop"]),
    (r"^tusk\.shared\.", "shared.contracts", "#d7f0d3",
     ["status", "logging", "mcp", "llm", "config", "interrupt", "stt", "tts"]),
    (r"^tusk\.providers\.", "providers", "#e0e8fb", ["llm", "stt", "tts"]),
    (r"^shells\.", "shells", "#f3e3fa", ["voice", "cli", "tray", "emulator"]),
    (r"^adapters\.", "adapters", "#fdf0c8", ["dictation", "gnome", "editor_emulator", "coding"]),
]

GRAPH_ATTRS = [
    'overlap="prism"', "splines=true", "pack=true", 'packmode="clust"',
    'sep="+15"', 'esep="+8"', 'fontname="Helvetica"',
]

NODE_RE = re.compile(r'^"([^"]+)"\s*\[')
Groups = dict[str, dict[str, list[str]]]


def cluster_for(node_id: str) -> tuple[str, str, str]:
    for pattern, name, color, sub_names in RULES:
        if re.match(pattern, node_id):
            sub = next((s for s in sub_names if f".{s}." in node_id), "root")
            return name, color, sub
    return "other", "#e8e8e8", "root"


def group_lines(body: str) -> tuple[Groups, dict[str, str], list[str]]:
    groups: Groups = {}
    colors: dict[str, str] = {}
    others: list[str] = []
    for line in filter(str.strip, body.splitlines()):
        place_line(groups, colors, others, line)
    return groups, colors, others


def place_line(groups: Groups, colors: dict[str, str], others: list[str], line: str) -> None:
    match = NODE_RE.match(line.strip())
    if match is None:
        others.append(line)
        return
    top, color, sub = cluster_for(match.group(1))
    colors[top] = color
    groups.setdefault(top, {}).setdefault(sub, []).append(line)


def emit_top(index: int, top: str, subs: dict[str, list[str]], color: str) -> list[str]:
    out = [f'subgraph cluster_{index} {{',
           f'  label="{top}"; style=filled; fillcolor="{color}"; fontsize=22; margin=24;']
    for sub_index, sub in enumerate(sorted(subs, key=lambda name: name == "root")):
        out.extend(emit_sub(index, sub_index, sub, subs[sub]))
    out.append("}")
    return out


def emit_sub(index: int, sub_index: int, sub: str, lines: list[str]) -> list[str]:
    if sub == "root":
        return [f"  {line}" for line in lines]
    header = [f'  subgraph cluster_{index}_{sub_index} {{',
              f'    label="{sub}"; style="solid,rounded"; color="#555555"; fontsize=15; margin=14;']
    return [*header, *(f"    {line}" for line in lines), "  }"]


def build(source_text: str, legend: str) -> str:
    header, body = source_text.split("{", 1)
    body, _ = body.rsplit("}", 1)
    groups, colors, others = group_lines(body)
    out = [header.strip(), "{", *GRAPH_ATTRS]
    for index, top in enumerate(sorted(groups)):
        out.extend(emit_top(index, top, groups[top], colors[top]))
    out.extend([legend, *others, "}"])
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} <pyreverse_classes.dot> <output.dot>")
        return 1
    legend_path = Path(__file__).with_name("full-class-graph-legend.gv")
    result = build(Path(argv[1]).read_text(encoding="utf-8"), legend_path.read_text(encoding="utf-8").strip())
    Path(argv[2]).write_text(result, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
