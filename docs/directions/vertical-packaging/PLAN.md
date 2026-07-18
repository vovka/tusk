# Plan: Vertical Packaging

**Branch:** `feature/adapter-allowlist`, then `feature/profiles` · **Depends on:** nothing
for the mechanism; individual presets mature as their directions land
([local-profile](../local-profile/README.md) → `local-private`,
[approvals](../approvals-and-audit-trail/README.md) → `accessibility`,
[coding-vertical](../coding-vertical/README.md) → `coding` at full strength) ·
**Unblocks:** per-vertical positioning ("TUSK for hands-free coding") the research calls
the fastest PMF path.

The mechanism is deliberately dumb: a profile **is** an env file layered under the user's
`.env`. One code change (adapter allowlist), one compose change, presets as data, a
guardrail test to stop drift. Ship the mechanism with two presets that work *today*
(coding, dictation); grow the list as other directions land.

## Milestone A — Adapter allowlist

### A1. Config + manager filter
- **Tests:** `tests/kernel/` — `TUSK_ADAPTERS="gnome,dictation"` → `AdapterManager`
  starts only those directories (matched by manifest `name`); empty/unset → all (current
  behavior); unknown name in the list → startup warning, not a crash. Hot-plug watcher
  respects the same filter.
- **Change:** `adapters_allowlist` in `tusk/shared/config/config_factory.py` (CSV parse,
  ≤10-line function); filter in `tusk/kernel/core/adapter_manager.py`.

### A2. Codex parity
- **Tests:** `tools/codex_mcp_config_generator.py` honors `TUSK_ADAPTERS` — generated
  `config.toml` contains only allowed servers.
- **Change:** same env read in the generator (keeps every backend's tool surface
  identical per package).

## Milestone B — Profiles as env presets

### B1. Preset files
- **Change:** new `profiles/` at repo root:
  - `default.env` — empty (documented no-op base).
  - `coding.env` — `TUSK_ADAPTERS=gnome,coding`, stronger `EXECUTOR_AGENT_LLM`, ack on.
  - `dictation.env` — `TUSK_ADAPTERS=gnome,dictation`, `TUSK_ACK=off` (silent flow),
    fast gatekeeper.
  Each file: comment header stating who it's for and what it changes. Presets contain
  **only** env keys that exist today — nothing speculative.

### B2. Compose layering
- **Tests:** manual matrix (documented in the PR): profile only, profile + `.env`
  override, no profile — user's `.env` always wins.
- **Change:** `docker-compose.yml` `env_file:` becomes
  `[profiles/${TUSK_PROFILE:-default}.env, .env]` (later file wins — `.env` last).
  Usage: `TUSK_PROFILE=coding docker compose up`.

### B3. Guardrail test
- **Tests:** `tests/style_guardrails/profile_guardrails.py` — every key in every
  `profiles/*.env` appears in `ConfigFactory`'s consumed-env set or an explicit
  passthrough allowlist (`GROQ_API_KEY`, `PULSE_*`, …). Renaming an env var now breaks the
  build instead of silently orphaning a preset.

## Milestone C — Per-profile smoke + docs

### C1. Smoke transcripts
- **Change:** one emulator transcript per shipped preset under `demos/`
  (`profile_coding_smoke.txt`, `profile_dictation_smoke.txt`) with run headers
  (the established `demos/*.txt` pattern). Manual runbook, not CI — the e2e harness's
  provider flakiness makes per-preset CI gating noise, not signal.
- **Verify:** each preset boots with `TUSK_SHELLS=emulator`, loads exactly its adapter
  set (assert via startup log), completes its transcript.

### C2. Quickstarts
- **Change:** README gains a short "Pick your TUSK" section: one block per preset —
  who it's for, the one-liner, prerequisites. Direction README updated with the shipped
  preset list.

## Milestone D — Presets that ride other directions (as they land)
- `local-private.env` — after local-profile D3 publishes validated models (that plan's
  `.env.local.example` graduates to a preset here).
- `accessibility.env` — after approvals lands (conservative flags: ack on, approval
  timeout long, all adapters); review wording with accessibility docs guidance.
- `coding.env` v2 — bump when the VS Code bridge lands (`TUSK_CODING_DRIVER` default).
Each is a data-only PR gated on its direction's acceptance criteria.

## Explicitly deferred
- **Prompt overrides** (`TUSK_PROMPT_DIR` etc.) — only when a shipped preset
  demonstrably needs vocabulary bias; resist building templating speculatively (the
  no-unrequested-abstractions rule applies to config too).
- **Prebuilt per-vertical images** — after presets stabilize; a preset must prove itself
  as data before it earns a build artifact.

## Acceptance criteria
- `TUSK_PROFILE=dictation docker compose up` runs with only gnome+dictation adapters,
  silent-ack flow, nothing else changed — verified by smoke transcript + startup log.
- Codex backend under a profile sees the same adapter set as the tusk backend.
- Guardrail test fails when a preset references a nonexistent env key.

## Risks
- Preset rot as flags evolve — B3 catches key renames; the smoke transcripts catch
  behavioral rot; keep the shipped list ≤ 4 presets (others live as documentation).
- Compose env-file interpolation differs across compose versions — pin the minimum
  compose version in README (verify during B2).
