# TUSK — Full Class Graph (experiment)

One SVG with all ~220 public classes across the whole codebase, laid out by
Graphviz's `fdp` (force-directed) engine instead of tiled by hand. Open
`full-class-graph.svg` in a browser: Ctrl+scroll (or Ctrl +/-) to zoom,
scrollbars/space-drag to pan. A small white "Legend" box is embedded in the
graph itself (`fdp` packs it wherever there's room, so its exact position
shifts on regeneration) explaining the three arrow styles pyreverse draws:

| Arrow | Meaning | Example |
| --- | --- | --- |
| Solid line, hollow triangle head, no label | Inheritance — arrow points from subclass to superclass | Dog → Animal ("Dog IS-A Animal") |
| Solid line, open "vee" head, green label | Association — arrow points **from the owner to the type it references**; label is the owner's attribute name | Car → Engine, label "engine" ("Car owns a single `engine` field") |
| Solid line, open diamond head, green label | Aggregation — arrow points **from the part to the owner** (opposite direction from association!); the diamond touches the owner; label is the owner's attribute name | Item → Container, label "items" ("Container owns the `items` collection") |

The direction flip between association and aggregation is the easy part to
mix up: for a plain arrow, the label is on the class at the **start**; for a
diamond arrow, the label is on the class at the **end** (where the diamond
sits). The embedded legend has all three side by side with these exact
examples so you don't have to hold the rule in your head.

## Why this layout

- Classes are grouped into 8 colored top-level clusters matching the package
  split in [class-diagrams.md](../class-diagrams.md) (kernel.core, kernel.agent,
  kernel.agent_backends, shared.contracts, shared.schemas, providers, shells,
  adapters), and each of those is further split into nested sub-clusters by
  immediate subpackage — e.g. `shells` contains `voice`/`cli`/`tray`/`emulator`
  boxes, `adapters` contains `gnome`/`dictation`/`coding`, `shared.contracts`
  contains `llm`/`stt`/`tts`/`mcp`/`config`/`status`/`logging`/`interrupt`.
  `fdp` supports true nested clusters, so each sub-cluster lays out as its own
  tight group first, then those groups get placed within the parent cluster.
- Within and between clusters (and sub-clusters), position is decided by
  `fdp`'s spring layout:
  classes with an edge (inheritance or a typed attribute) pull toward each
  other; everything else just gets packed in efficiently. This is why
  `shared.contracts` (the ABCs almost every other package depends on) settles
  near the center with edges fanning out to shells/providers/adapters/kernel,
  rather than sitting wherever a manual grid would have put it.
- A first attempt used `dot` (hierarchical layout), which strung all 8
  clusters into a single 52,000pt-wide ribbon — `dot` ranks nodes by longest
  path and packs disconnected components left-to-right in a row. `fdp` was
  used instead specifically because it 2D-packs disconnected components and
  fully supports cluster bounding boxes (`sfdp` does not).

## Caveat

Only ~40 edges get drawn across ~220 classes. This codebase leans on
constructor-injected duck typing (per `architecture.md`), which static
analysis can't see — so most placement within a cluster is just compact
packing, not a relationship signal. Cross-cluster lines are real detected
relationships (inheritance or a typed, named attribute), not noise.

## Regenerate

```bash
docker exec -u root <container> bash -c "apt-get install -y graphviz && pip install pylint"
docker exec <container> bash -c "cd /app && pyreverse -o dot -p full --filter-mode=PUB_ONLY -d /tmp/dg tusk shells adapters"
python3 generate_full_class_graph.py /tmp/dg/classes_full.dot full-class-graph.dot
docker exec <container> fdp -Tsvg /path/to/full-class-graph.dot -o full-class-graph.svg
```

`generate_full_class_graph.py` wraps pyreverse's raw per-class DOT output into
nested `subgraph cluster_*` blocks (top-level package, then subpackage) and
sets the `fdp`-friendly graph attributes (`overlap`, `pack`, `packmode`,
separation). The package→cluster mapping is the `RULES` list at the top of the
script — each entry is `(top pattern, cluster name, color, [sub-cluster
names])`, where a class joins sub-cluster `S` when its qualified name contains
`.S.`; edit those if packages get reorganized. Any class whose fully qualified
name matches no sub-cluster falls into that package's `root` group
(undecorated, no inner box) rather than being dropped. The embedded legend is
kept as plain DOT in `full-class-graph-legend.gv` next to the script.

## Known rough edges (v2, unreviewed)

- A few long edges cut straight through unrelated clusters — cosmetic only.
- `kernel.core` and `kernel.agent_backends` clusters sit flush against each
  other with no gap; bump `sep`/`esep` in the script if that should change.
- Sub-clusters are undecorated rounded boxes (border only, no fill) so the
  parent's fill color still shows through — if a package gets a 3rd nesting
  level (e.g. `shells.voice.stages.gate`) it isn't broken out separately yet.
