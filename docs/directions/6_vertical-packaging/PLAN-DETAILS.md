# Vertical Packaging — Fine-Grained Execution Plan

Commit-by-commit detail for [PLAN.md](PLAN.md), grounded against `main` @ `3fb169d`.
Tests: `docker compose exec tusk pytest tests/kernel/ tests/style_guardrails/ tests/shared/`.

## Grounding notes

- `AdapterManager.start_all` iterates directories and `start_adapter` reads the manifest
  before connecting (`adapter_manager.py:29-45`) — filtering by manifest `name` inside
  `start_adapter` covers the watcher path for free (`AdapterWatcher.on_created` calls the
  same method, `adapter_watcher.py:13-15`).
- `ConfigFactory` is the single env reader (`config_factory.py`); `Config` is frozen —
  one new field.
- The codex generator globs the same manifests and currently hardcodes
  `command = "python3"` (`codex_mcp_config_generator.py:18, 32-41`); it reads env in
  `main()` (`:44-47`) — the allowlist hook goes there.

## Milestone A — Adapter allowlist

### Commit A1 — config + manager filter
- **Tests** (`tests/kernel/`):
  - `TUSK_ADAPTERS="gnome,dictation"` → only those adapters start (fixture adapters dir);
  - unset/empty → all start (exact current behavior);
  - unknown name in the list → one startup warning naming it, no crash;
  - watcher-added adapter not in the allowlist → skipped (call `start_adapter` directly).
- **Change:** `ConfigFactory` — `adapters_allowlist: tuple[str, ...]` parsed CSV in
  `_environment_values` (empty tuple = all); `Config` field; `AdapterManager.__init__`
  gains `allowlist: tuple[str, ...] = ()` and `start_adapter` returns early after
  `_manifest` when `allowlist and name not in allowlist` (`adapter_manager.py:36-43`,
  two lines + warning branch); `startup.py` passes it.

### Commit A2 — codex generator parity
- **Tests** (`tests/` for `tools/`): generator with `TUSK_ADAPTERS=gnome` emits only the
  gnome section; unset emits all (current behavior).
- **Change:** `codex_mcp_config_generator.py` — `main()` reads `TUSK_ADAPTERS`, passes an
  allowlist into the class; `_section` skips non-allowed names. (~6 lines.)

## Milestone B — Profiles as env presets

### Commit B1 — preset files
- **Change:** new `profiles/` at repo root, keys strictly from today's `ConfigFactory`
  vocabulary (`config_factory.py:12, 46-60, 69-97`):
  - `default.env` — empty file with a comment ("no-op base; TUSK_PROFILE defaults here").
  - `coding.env`:
    ```
    # TUSK for hands-free coding: gnome + coding adapters, stronger executor.
    TUSK_ADAPTERS=gnome,coding
    EXECUTOR_AGENT_LLM=groq/openai/gpt-oss-120b
    TUSK_ACK=on
    ```
  - `dictation.env`:
    ```
    # TUSK for dictation/writing: silent flow, fast gatekeeper.
    TUSK_ADAPTERS=gnome,dictation
    TUSK_ACK=off
    GATEKEEPER_LLM=groq/llama-3.1-8b-instant
    ```
  Nothing speculative: every key must already exist (B3 enforces it).
- **Note:** presets do not touch `TUSK_SHELLS` — shell choice is per-user, not
  per-vertical.

### Commit B2 — compose layering
- **Change:** `docker-compose.yml` — the service's `env_file:` becomes
  ```yaml
  env_file:
    - profiles/${TUSK_PROFILE:-default}.env
    - .env
  ```
  (later file wins in compose — the user's `.env` always overrides the preset). Usage:
  `TUSK_PROFILE=coding docker compose up`. Pin the minimum compose version that
  interpolates `env_file` entries in the README (verify on the dev machine during this
  commit; it's the one compose-version-sensitive piece).
- **Tests:** manual matrix recorded in the PR: no profile / profile only / profile +
  overriding `.env` — assert the effective adapter set from the startup log each time.

### Commit B3 — preset guardrail
- **Tests:** `tests/style_guardrails/profile_guardrails.py`:
  - parse every `profiles/*.env` (simple `KEY=VALUE` lines, `#` comments);
  - the consumed-key set = regex over `tusk/shared/config/config_factory.py` source for
    `os.environ.get("NAME")` / `os.environ["NAME"]` / `self._slot("NAME"` /
    `self._int("NAME"` / `self._float("NAME"` / `self._bool("NAME"` — plus an explicit
    passthrough allowlist constant (`GROQ_API_KEY`, `OPENROUTER_API_KEY`, `PULSE_SINK`,
    `PULSE_SOURCE`, `CODING_AGENT_MODEL`, `LOCAL_LLM_BASE_URL`, …: env consumed outside
    `ConfigFactory` — adapters and compose);
  - every preset key must be in the union; failure message names the file, the key, and
    the fix ("renamed? update the preset").
  This is the same source-scraping trick `import_guardrails.py` already plays — cheap
  and honest.

## Milestone C — Smoke + docs

### Commit C1 — per-preset smoke transcripts
- **Change:** `demos/profile_coding_smoke.txt`, `demos/profile_dictation_smoke.txt` with
  the established run-header pattern (`demos/coding_session_emulated.txt`); each: boot
  with `TUSK_PROFILE=<name> TUSK_SHELLS=emulator`, assert the startup log lists exactly
  the preset's adapters, run 3–4 utterances exercising the vertical's core loop.
- **Verify:** manual runbook, not CI (e2e provider flakiness = noise as a gate; the
  startup-log adapter assertion is the deterministic part).

### Commit C2 — quickstarts
- **Change:** README "Pick your TUSK" section — one block per shipped preset: who it's
  for, the one-liner, prerequisites; this direction's README gets the shipped-preset
  list + status.

## Milestone D — Presets riding other directions (data-only PRs, gated on their acceptance criteria)

| Preset | Lands after | Content beyond B1 pattern |
|---|---|---|
| `local-private.env` | direction 5 D3 (validated models) | the validated slot set + `STT_ENGINE=whisper`, `TUSK_TTS_ENGINE=piper` |
| `accessibility.env` | direction 1 (approvals) | all adapters, `TUSK_ACK=on`, `TUSK_APPROVAL_TIMEOUT_SECONDS=120` |
| `coding.env` v2 | direction 4 B3 (bridge) | `TUSK_CODING_DRIVER` default + note |

## Edge cases

| Case | Behavior |
|---|---|
| `TUSK_PROFILE=nonexistent` | compose fails fast on a missing env_file — clear error, documented |
| Preset sets an adapter that doesn't exist locally | allowlist warning at startup (A1), everything else runs |
| User `.env` contradicts the preset | user wins by layering order — by design, documented |
| Preset key renamed in a refactor | B3 guardrail fails the build naming the orphan |

## Explicitly not building (v1)
Prompt overrides / `TUSK_PROMPT_DIR` (build only when a shipped preset demonstrably needs
vocabulary bias); prebuilt per-vertical images; a profile *registry* class (the env-file
layering **is** the mechanism — a config object on top of it is the abstraction the
guardrails tell us not to add); more than 4 shipped presets.

## Open items to confirm during implementation
1. Compose version on the dev machine vs. `env_file` interpolation (B2 — verify first).
2. The passthrough allowlist contents for B3 (grep adapters + compose for env reads at
   implementation time; keep the constant next to the test).
3. Whether the startup log already prints the loaded adapter list (C1 assertion hook) —
   if not, one log line in `AdapterManager.start_all` rides with A1.
