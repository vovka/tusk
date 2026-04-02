---
name: svg-to-png
description: Convert an SVG file to PNG using Inkscape in Docker; no host dependencies required
allowed-tools: Read, Bash, Write, Glob
---

# SVG to PNG via Docker (Inkscape)

## When to Use This

- When an SVG diagram in the repo needs to be rendered as a PNG for use in Markdown docs
- When `rsvg-convert`, `inkscape`, or `cairosvg` are not installed on the host
- Triggered by: "convert this SVG to an image", "render the diagram", "save svg as png"

## Core Workflow

### Step 1: Locate the SVG

Find the source `.svg` file. If the SVG is inline in a Markdown file, extract it first:

```bash
# Extract inline SVG from a .md file (adjust line range)
sed -n '<start>,<end>p' docs/architecture.md > docs/diagrams/architecture.svg
```

### Step 2: Convert with Docker

Use `minidocks/inkscape` — it is small, has no GUI deps, and works headless.

```bash
docker run --rm \
  -v <host-dir>:/work \
  minidocks/inkscape:latest \
  inkscape /work/<file>.svg \
    --export-type=png \
    --export-filename=/work/<file>.png \
    --export-width=1360
```

- Mount the **directory** containing the SVG, not just the file.
- `--export-width=1360` gives 2× resolution for retina; adjust as needed.
- Inkscape prints two GObject warnings on startup — these are harmless, output is correct.

### Step 3: Verify

```bash
ls -lh <host-dir>/<file>.png
```

Then read the PNG with the Read tool to visually inspect the result before committing.

### Step 4: Reference in Markdown

Replace any inline SVG block with:

```markdown
![Alt text](diagrams/<file>.png)

> Source: [`docs/diagrams/<file>.svg`](diagrams/<file>.svg)
```

Use a Python one-liner to do this reliably when the SVG is embedded in a large file:

```python
with open('docs/architecture.md', 'r') as f:
    content = f.read()
svg_start = content.index('<svg ')
svg_end   = content.index('</svg>') + len('</svg>')
replacement = '![Diagram](diagrams/architecture.png)\n\n> Source: [`docs/diagrams/architecture.svg`](diagrams/architecture.svg)'
with open('docs/architecture.md', 'w') as f:
    f.write(content[:svg_start] + replacement + content[svg_end:])
```

## File Conventions in This Project

| File | Path |
|---|---|
| SVG source | `docs/diagrams/<name>.svg` |
| Rendered PNG | `docs/diagrams/<name>.png` |
| Markdown reference | `![...](diagrams/<name>.png)` |

## Common Pitfalls

- **Mount the directory, not the file.** Inkscape writes the output next to the input; a file mount won't work.
- **`width="100%"` in the SVG** renders at a fixed pixel size determined by `viewBox`. Always pass `--export-width` explicitly.
- **GObject warnings** on stderr are not errors — check the exit code and output file instead.
- **Image too small?** Increase `--export-width`. Current project default is 1360 (2× the 680px viewBox width).
