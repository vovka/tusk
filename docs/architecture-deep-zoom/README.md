# TUSK deep-zoom architecture

This package contains the source-recovered architecture map created from revision `0e8f2d7760ea98ed28f5e78462b9adc5c536cb09` of `vovka/tusk`.

Existing architecture documentation and diagrams were deliberately excluded from the investigation. Evidence came from production source, adapter manifests, configuration, dependency declarations, Docker deployment files, and tests.

## Files

- `/architecture-deep-zoom.svg` - standalone browser-viewable deep-zoom diagram.
- `tools/architecture-deep-zoom/generate.py` - deterministic SVG generator.
- `tools/architecture-deep-zoom/validate.py` - structural validation and optional Inkscape rendering.
- `tools/architecture-deep-zoom/render_previews.sh` - regenerates PNG validation views.
- `docs/architecture-deep-zoom/validation-report.json` - recorded validation output.
- `docs/architecture-deep-zoom/evidence.md` - recovered hierarchy, supported relationships, inferences, omissions, and ambiguities.

## Reproduce

```bash
python tools/architecture-deep-zoom/generate.py architecture-deep-zoom.svg
python tools/architecture-deep-zoom/validate.py \
  --render-dir /tmp/tusk-architecture-validation \
  --json docs/architecture-deep-zoom/validation-report.json
```

To regenerate PNG previews:

```bash
tools/architecture-deep-zoom/render_previews.sh
```

The SVG has no JavaScript, external fonts, external images, or network dependencies.
