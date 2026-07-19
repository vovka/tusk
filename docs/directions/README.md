# Development Directions — Implementation Order

Derived from the [market research](../market-research-reddit-2026-07.md) and the
per-direction architecture assessments. Directory prefixes are the implementation order.
It is a *priority* order, not a strict schedule — the parallelism map below shows what can
ride alongside.

| # | Direction | Why this position |
|---|---|---|
| 1 | [approvals-and-audit-trail](1_approvals-and-audit-trail/README.md) | Critical path: unblocks every real-world write tool; completes the research's step-1 core; kernel-only, no external moving parts |
| 2 | [reliability-and-wayland](2_reliability-and-wayland/README.md) | The research's #1 repeated pain ("breaks after OS updates"); supervision + mic recovery are cheap and benefit everything; Wayland keyboard input is existential for the current reference platform (GNOME on Linux) and establishes the platform-backend pattern every future desktop adapter reuses |
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

## Platform scope

TUSK's core is OS-agnostic by design (`docs/brief.md`, principle 6: "The core is
platform-agnostic by definition — it emits semantic events, not platform calls"). GNOME
on Linux is the **first reference platform**, not the target: every other desktop
environment and OS arrives as a new adapter plus per-platform provider backends, with no
kernel or shell changes. The directions respect that boundary:

- Direction 2's portal input backend rides `org.freedesktop.portal.*` — a freedesktop
  standard implemented by GNOME, KDE, and wlroots compositors alike; only the
  window-control shell extension is GNOME-specific, and per-DE equivalents (e.g. KWin
  scripting) are future backends behind the same seam.
- Direction 4's VS Code bridge (socket + extension) is inherently cross-OS; it becomes
  useful on Windows/macOS the moment a desktop adapter for those platforms exists.
- Directions 3, 5, 6 are platform-neutral already (MCP servers, OpenAI-compatible local
  engines, env presets).

Known OS-coupled points *outside* the adapters, each already behind a seam for future
per-platform backends: the host launcher daemon (Unix socket), `paplay` speech playback,
the PulseAudio echo-cancel routing in compose, and the AppIndicator tray backend (the
`TrayBackend` ABC exists for exactly this). A Windows/macOS/KDE port = one new adapter
directory + implementations behind these seams — no direction plan bakes in the contrary.

## Per-directory contents

Each direction directory contains: `README.md` (architecture assessment), a mermaid
diagram, `PLAN.md` (milestone plan), `PLAN-DETAILS.md` (commit-by-commit execution detail,
grounded in code with file:line anchors — where it contradicts the older assessment or
PLAN.md, the details file wins; corrections are marked).
