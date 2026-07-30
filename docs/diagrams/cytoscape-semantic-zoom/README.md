# TUSK semantic-zoom architecture map

This directory contains a source-derived interactive architecture diagram generated from repository commit `0e8f2d7760ea98ed28f5e78462b9adc5c536cb09`.

## Artifacts

- `tusk-cytoscape-architecture.html` — standalone, offline-capable Cytoscape.js diagram with complete architecture data and interaction logic.
- `tusk-arch-agent-orchestrator.png` — focused browser-rendered preview of the built-in agent orchestration area.

## Reproducible support files

- `assemble.py` reconstructs the standalone HTML from the compressed template/application payload and pinned Cytoscape.js.
- `render_preview.py` opens the generated HTML in Chromium and captures the focused preview.
- `payload/` stores the compressed source-derived template and application model.
- `.github/workflows/build-cytoscape-architecture.yml` assembles and validates the deliverables on the branch.

Open the HTML file directly in a normal browser. Existing architecture documentation and diagrams were intentionally not used as architecture evidence; the model was recovered from source code, executable configuration, adapter manifests, deployment configuration, and tests.
