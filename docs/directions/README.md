# Development Directions — Implementation Order

Derived from the [market research](../market-research-reddit-2026-07.md) and the
per-direction architecture assessments. Directory prefixes are the implementation order.
It is a *priority* order, not a strict schedule — the parallelism map below shows what can
ride alongside.

| # | Direction | Why this position |
|---|---|---|
| 1 | [approvals-and-audit-trail](1_approvals-and-audit-trail/README.md) | Critical path: unblocks every real-world write tool; completes the research's step-1 core; kernel-only, no external moving parts |
| 2 | [reliability-and-wayland](2_reliability-and-wayland/README.md) | The research's #1 repeated pain ("breaks after OS updates"); supervision + mic recovery are cheap and benefit everything; Wayland keyboard input is existential for the Linux/GNOME target |
| 3 | [real-world-adapters](3_real-world-adapters/README.md) | The loudest mainstream demand (email/calendar "that actually does things"); reads can ship during 2, writes flip on the day 1 lands |
| 4 | [coding-vertical](4_coding-vertical/README.md) | TUSK's differentiator vs. Talon; adapter-side grounding is a quick win, the VS Code bridge is the strategic piece |
| 5 | [local-profile](5_local-profile/README.md) | Privacy is a top-3 adoption factor; plumbing is small but the validation campaign is long-running — start it early, let it finish when it finishes |
| 6 | [vertical-packaging](6_vertical-packaging/README.md) | Packages the outcomes of 1–5 into sellable presets; the mechanism is trivial and can land anytime, but the direction *completes* last by nature |

## Parallelism map

Independent starts that can run alongside direction 1 in separate worktrees, touching
disjoint files:

- **2A/2B** (adapter supervision, mic/STT recovery) — kernel `core/` + `shells/voice/` + providers.
- **3A** (MCP dialect hardening) — `tusk/shared/mcp/` + fixtures only.
- **4A** (tree-sitter grounding + targeted edit operations) — `adapters/coding/` only.
- **5A/5B** (local LLM + TTS providers) — `tusk/providers/` only.
- **6A** (adapter allowlist) — a few lines in config + `AdapterManager` + the codex generator.

Hard dependency edges: **3D (writes) → 1B (approval flow)** · **6 presets → their source
directions** · everything else is soft ordering by value.

Each direction directory contains: `README.md` (architecture assessment), a mermaid
diagram, `PLAN.md` (milestone plan), `PLAN-DETAILS.md` (commit-by-commit execution detail,
grounded in code with file:line anchors — where it contradicts the older assessment or
PLAN.md, the details file wins; corrections are marked).
