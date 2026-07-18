# Direction: Vertical Packaging (purpose-specific bundles)

**Research basis:** "vertical packages instead of an assistant for everyone" — the fastest
PMF path is ready-made bundles for hands-free coding, dictation/writing, accessibility
desktop control, back-office automation
([market research](../../market-research-reddit-2026-07.md)).
**Verdict:** almost entirely additive configuration work. A vertical is largely
expressible as an env preset *today*; the only structural touch is adapter filtering in
`AdapterManager`. The architecture's env-driven factories make bundles cheap — the real
work is choosing and tuning them, not enabling them.

**Diagram:** [profile layering](profile-layering.md)

## What the architecture already provides

- **Frozen env-driven config.** `Config.from_env()` (`ConfigFactory`) already controls:
  shells (`TUSK_SHELLS`), all six LLM slots, STT engine, TTS/ACK toggles, agent backend,
  tray options. A coherent vertical differs mostly in these values.
- **Modular surfaces.** Shells are independent (voice/cli/tray); dictation/coding modes
  activate only when their tools are invoked; adapters are directory-discovered processes.
- **Backend consistency.** The codex config generator derives from the same `adapter.json`
  manifests, so a package's tool surface stays identical across agent backends.
- **Per-context prompt precedent.** Mode gate prompts (`DICTATION_GATE_PROMPT` /
  `CODING_GATE_PROMPT`) already show prompt variation injected at wiring time.
- **Compose layering.** `env_file` lists and compose override files are standard Docker
  mechanics — no custom machinery needed for preset-then-user-overrides.

## Gaps

- **No adapter selection.** `AdapterManager.start_all()` loads every `adapters/*` directory —
  a dictation-only package cannot exclude `coding`/future PIM adapters without deleting
  directories.
- **No named-profile concept.** Users must hand-assemble ~10 env vars coherently; nothing
  ships known-good bundles (this is also where the local-profile direction's validated
  configs should land).
- **Prompts are code.** Agent-profile system prompts live in `agent_profiles.py`; a vertical
  needing vocabulary bias (coding: symbols/jargon; accessibility: simpler confirmations)
  has no override point short of forking.
- **Single distribution shape.** One compose file, one README path — no per-vertical
  quickstart.

## Required changes

1. **[kernel]** `TUSK_ADAPTERS` allowlist (empty = all): `AdapterManager` filters discovered
   directories; the codex config generator respects the same variable. A few lines each.
2. **[packaging]** `profiles/<name>.env` presets (coding, dictation, accessibility,
   local-private) + compose `env_file` layering so `.env` overrides the preset. A profile
   *is* an env file — no new config system, `Config` stays frozen.
3. **[docs]** Per-vertical quickstarts ("TUSK for hands-free coding" one-liner: profile +
   compose override + prerequisites).
4. **[kernel, deferred]** Prompt overrides (e.g. `TUSK_PROMPT_DIR` with per-profile
   suffix files) — only when a concrete vertical demonstrably needs vocabulary bias;
   resist building a prompt-templating system speculatively.
5. **[later]** Distribution packaging (prebuilt per-vertical images) once presets stabilize.

## Risks & notes

- Preset drift: profiles reference env vars that later rename — cover with a guardrail test
  that loads every `profiles/*.env` through `ConfigFactory` and asserts no unknown keys.
- Combinatorics: verticals × backends × local/cloud multiply the test matrix; keep the
  shipped preset list short (3–4) and let others be documentation, not artifacts.
- The tray/e2e/emulator shells make per-profile smoke tests cheap (`TUSK_SHELLS=emulator`
  + transcript per vertical) — worth adding per shipped preset.
