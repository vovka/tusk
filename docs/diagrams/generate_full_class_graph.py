#!/usr/bin/env python3
"""Wrap a pyreverse classes .dot file into nested per-package subgraph clusters."""
import re
import sys

# (top pattern, top name, top color, [(sub pattern, sub name), ...])
RULES = [
    (r"^tusk\.kernel\.agent_backends\.", "kernel.agent_backends", "#fde8e8", [
        (r"\.agent_backends\.codex_mcp\.", "codex_mcp"),
    ]),
    (r"^tusk\.kernel\.agent\.", "kernel.agent", "#f8d9d9", [
        (r"\.agent\.session\.", "session"),
        (r"\.agent\.runtime\.", "runtime"),
        (r"\.agent\.planner\.", "planner"),
        (r"\.agent\.tool_sequence\.", "tool_sequence"),
        (r"\.agent\.guards\.", "guards"),
    ]),
    (r"^tusk\.kernel\.", "kernel.core", "#fbe5c8", [
        (r"\.kernel\.interfaces\.", "interfaces"),
        (r"\.kernel\.modes\.", "modes"),
        (r"\.kernel\.tools\.", "tools"),
    ]),
    (r"^tusk\.shared\.schemas\.", "shared.schemas", "#e3f2e1", [
        (r"\.schemas\.tools\.", "tools"),
        (r"\.schemas\.desktop\.", "desktop"),
    ]),
    (r"^tusk\.shared\.", "shared.contracts", "#d7f0d3", [
        (r"\.shared\.status\.", "status"),
        (r"\.shared\.logging\.", "logging"),
        (r"\.shared\.mcp\.", "mcp"),
        (r"\.shared\.llm\.", "llm"),
        (r"\.shared\.config\.", "config"),
        (r"\.shared\.interrupt\.", "interrupt"),
        (r"\.shared\.stt\.", "stt"),
        (r"\.shared\.tts\.", "tts"),
    ]),
    (r"^tusk\.providers\.", "providers", "#e0e8fb", [
        (r"\.providers\.llm\.", "llm"),
        (r"\.providers\.stt\.", "stt"),
        (r"\.providers\.tts\.", "tts"),
    ]),
    (r"^shells\.", "shells", "#f3e3fa", [
        (r"^shells\.voice\.", "voice"),
        (r"^shells\.cli\.", "cli"),
        (r"^shells\.tray\.", "tray"),
        (r"^shells\.emulator\.", "emulator"),
    ]),
    (r"^adapters\.", "adapters", "#fdf0c8", [
        (r"^adapters\.dictation\.", "dictation"),
        (r"^adapters\.gnome\.", "gnome"),
        (r"^adapters\.editor_emulator\.", "editor_emulator"),
        (r"^adapters\.coding\.", "coding"),
    ]),
]


def cluster_for(node_id: str) -> tuple[str, str, str]:
    for pattern, name, color, sub_rules in RULES:
        if re.match(pattern, node_id):
            for sub_pattern, sub_name in sub_rules:
                if re.search(sub_pattern, node_id):
                    return name, color, sub_name
            return name, color, "root"
    return "other", "#e8e8e8", "root"


def node_id_of(line: str) -> str:
    return re.match(r'"([^"]+)"', line).group(1)


LEGEND = r"""
subgraph cluster_legend {
  label="Legend"; style=filled; fillcolor="#ffffff"; color="black"; fontsize=22; margin=24;
  node [shape=box, style=filled, fillcolor="white", fontsize=13, fontname="Helvetica"];
  edge [fontname="Helvetica", fontsize=12];

  Leg_tip [shape=plaintext, fontsize=11, fontcolor="#444444",
    label="Tip: the green label names an attribute.\nPlain arrow -> it's on the class the arrow STARTS from.\nDiamond arrow -> it's on the class the arrow ENDS at (diamond touches the owner)."];

  Leg_sub [label="Dog"];
  Leg_super [label="Animal"];
  Leg_sub -> Leg_super [arrowhead="empty", arrowtail="none"];
  Leg_cap1 [shape=plaintext, fontsize=11, fontcolor="#444444",
    label="Dog inherits from Animal\n(Dog IS-A Animal)"];
  Leg_super -> Leg_cap1 [style=invis];

  Leg_a [label="Car"];
  Leg_b [label="Engine"];
  Leg_a -> Leg_b [arrowhead="vee", arrowtail="none", fontcolor="green", label="  engine"];
  Leg_cap2 [shape=plaintext, fontsize=11, fontcolor="#444444",
    label="Car has an Engine\n(Car owns a single 'engine' field)"];
  Leg_b -> Leg_cap2 [style=invis];

  Leg_item [label="Item"];
  Leg_container [label="Container"];
  Leg_item -> Leg_container [arrowhead="odiamond", arrowtail="none", fontcolor="green", label="  items"];
  Leg_cap3 [shape=plaintext, fontsize=11, fontcolor="#444444",
    label="Container has many Items\n(Container owns the 'items' collection)"];
  Leg_container -> Leg_cap3 [style=invis];

  Leg_tip -> Leg_sub [style=invis];
  Leg_cap1 -> Leg_a [style=invis];
  Leg_cap2 -> Leg_item [style=invis];
}
""".strip()


def main(src_path: str, dst_path: str) -> None:
    text = open(src_path, encoding="utf-8").read()
    header, body = text.split("{", 1)
    body, _ = body.rsplit("}", 1)

    node_re = re.compile(r'^"([^"]+)"\s*\[', re.MULTILINE)
    top_groups: dict[str, dict[str, list[str]]] = {}
    top_colors: dict[str, str] = {}
    other_lines = []
    for line in body.splitlines():
        match = node_re.match(line.strip())
        if match:
            top, color, sub = cluster_for(match.group(1))
            top_colors[top] = color
            top_groups.setdefault(top, {}).setdefault(sub, []).append(line)
        elif line.strip():
            other_lines.append(line)

    out = [
        header.strip(), "{",
        'overlap="prism"', 'splines=true', 'pack=true', 'packmode="clust"',
        'sep="+15"', 'esep="+8"', 'fontname="Helvetica"',
    ]
    for i, top in enumerate(sorted(top_groups)):
        subs = top_groups[top]
        out.append(f'subgraph cluster_{i} {{')
        out.append(f'  label="{top}"; style=filled; fillcolor="{top_colors[top]}"; '
                    f'fontsize=22; margin=24;')
        for j, sub in enumerate(sorted(subs, key=lambda s: s == "root")):
            lines = subs[sub]
            if sub == "root":
                out.extend(f"  {l}" for l in lines)
                continue
            out.append(f'  subgraph cluster_{i}_{j} {{')
            out.append(f'    label="{sub}"; style="solid,rounded"; color="#555555"; '
                        f'fontsize=15; margin=14;')
            out.extend(f"    {l}" for l in lines)
            out.append("  }")
        out.append("}")
    out.append(LEGEND)
    out.extend(other_lines)
    out.append("}")

    open(dst_path, "w", encoding="utf-8").write("\n".join(out))
    summary = {top: sorted(subs) for top, subs in top_groups.items()}
    print(f"clusters: {summary}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
