# TUSK — Task Unified Speech Kernel

## Project Brief v0.5

---

## 1. Vision

TUSK is a universal, always-listening desktop AI voice assistant that gives users hands-free, voice-driven control over their entire computing environment. It doesn't wait to be summoned — it listens, understands, and acts.

**TUSK is AI-first.** At its core is not a command parser or a script runner — it's an AI agent. The main agent orchestrates the system, spawns sub-agents for complex or parallel tasks, and each agent can run on a different LLM. Models and providers can be hot-swapped on the fly — by voice. Say "Tusk, use Opus 4.6 for the main agent" and it switches. This is not an app with AI bolted on; the AI *is* the app.

Think Jarvis, but real, open, and not locked to any ecosystem.

No existing voice assistant delivers this. Siri, Cortana, Google Assistant, and Alexa are all walled-garden products tied to specific platforms, with shallow desktop integration at best. TUSK is designed from the ground up to be **environment-agnostic, provider-agnostic, and modular** — every component can be swapped, extended, or replaced.

The long-term ambition is to become the **industry standard for voice-driven human-computer interaction**.

---

## 2. Problem Statement

- **Keyboard and mouse are bottlenecks.** For many workflows — multitasking, window management, app launching, repetitive actions — physical input is slower than speech.
- **Existing voice assistants are ecosystem-locked.** They work within their walled gardens and offer limited desktop-level control.
- **Accessibility is underserved.** Users who cannot rely on traditional input devices lack a powerful, general-purpose alternative.
- **No assistant truly "always listens."** Current solutions require explicit wake words, button presses, or are limited to narrow command sets. None offer continuous, intelligent ambient awareness.

---

## 3. Core Concept — How It Works

### 3.1 Core vs. Extensions

TUSK has a strict architectural boundary between **Core** and **Extensions**:

**Core (the kernel)** — three modules, nothing else:

1. **Voice-to-Text Module** — always-on microphone capture + STT engine (Whisper). Produces a continuous stream of transcribed text.
2. **AI Agent** — the main orchestrator. Receives transcribed text via the gatekeeper tier, consumes environmental context from context-provider extensions, understands intent, plans actions, and emits structured events.
3. **Sub-Agents Subsystem** — the main agent can spawn sub-agents for complex, multi-step, or parallel tasks. Each sub-agent runs on a configurable LLM and reports back to the main agent.

The core's job is: **listen to voice → consume context → understand intent → emit events.** The core does not directly interact with any operating system, desktop environment, or application. It works with a **unified context format** (structured data describing the environment — active windows, focused app, screen layout, etc.) and produces **semantic events** (e.g., `open_application`, `move_window`, `type_text`). Where the context comes from and how events are executed — that's the extensions' job.

**Extensions** — pluggable modules that communicate bidirectionally with the core. There are two types:

**Context Providers** (environment → core): These extensions observe the user's environment and feed structured context data into the core agent. The agent needs this context to reason correctly — "close this window" is meaningless without knowing which window is focused; "move it to the right" requires knowing the current layout. Context providers are inherently platform-specific (a GNOME context provider reads D-Bus, a Windows one reads Win32 APIs), but the core consumes a **unified context schema** regardless of source.

**Action Executors** (core → environment): These extensions subscribe to semantic events emitted by the core and translate them into platform-specific operations — opening windows, pressing keys, moving the mouse, launching apps.

A single extension can be both a context provider and an action executor. The built-in Linux/GNOME extension, for example, does both: it provides desktop context (window list, focus state, workspace layout) *and* executes desktop actions (move windows, launch apps, control input).

- Anyone can create an extension. Extensions are discovered, loaded, and registered at runtime.
- TUSK ships with a **built-in Linux/GNOME desktop extension** as the first reference implementation. But this is an extension, not part of the core.
- Future extensions could include: Windows desktop, macOS desktop, smart home integration, browser automation, IDE integration, custom workflow automation, etc.

This separation means the core is portable, testable, and fully platform-agnostic. New platforms and capabilities are added by writing extensions — the kernel never changes.

### 3.2 Speech-to-Action Pipeline

```
┌─────────────────────────────────────────────────────────┐
│  CORE (the kernel)                                      │
│                                                         │
│  Microphone (always on)                                 │
│      → Voice-to-Text Module (Whisper, local)            │
│      → Raw transcript stream                            │
│      → TIER 1: GATEKEEPER MODEL (cheap, fast LLM)      │
│      │   "Is this speech directed at TUSK?"             │
│      │       ├─ No  → discard                           │
│      │       └─ Yes → forward to main agent             │
│      │                                                  │
│      → TIER 2: MAIN AI AGENT (smart, capable LLM)      │
│          Inputs:                                        │
│            • command text (from gatekeeper)              │
│            • environment context (from extensions)       │
│          Outputs:                                       │
│            • semantic events → extensions                │
│            • sub-agent spawns → sub-agent subsystem      │
│                                                         │
└──────────────────────┬──────────────────────────────────┘
                       │ events ↓        ↑ context
                       │                 │
┌──────────────────────▼─────────────────┴────────────────┐
│  EXTENSIONS (pluggable, bidirectional)                   │
│                                                         │
│  ┌─────────────────────────────────────────────┐        │
│  │ Linux/GNOME Desktop Extension (built-in)    │        │
│  │                                             │        │
│  │  CONTEXT PROVIDER (→ core):                 │        │
│  │   • active window, focused app              │        │
│  │   • window list, positions, sizes           │        │
│  │   • workspace layout, screen geometry       │        │
│  │   • running applications                    │        │
│  │                                             │        │
│  │  ACTION EXECUTOR (← core):                  │        │
│  │   • open/close/resize/move/focus windows    │        │
│  │   • launch applications                     │        │
│  │   • keyboard input, mouse control           │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│  ┌─────────────────────────────────────────────┐        │
│  │ Future: Windows Extension (context + action)│        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│  ┌─────────────────────────────────────────────┐        │
│  │ Future: Custom User Extension               │        │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### 3.3 Two-Tier LLM Architecture

**Why two tiers?** STT transcribes everything — every conversation in the room, every TV in the background. Sending all of that to a powerful (expensive, slower) model would be wasteful and slow. Instead, a cheap and fast gatekeeper model handles the high-volume, low-complexity job of filtering: *"is this for me?"* Only confirmed commands reach the main agent, which uses a smarter model for understanding, planning, and execution.

Both tiers are fully configurable. By default, the gatekeeper runs the cheapest available model (e.g., Haiku, GPT-4o-mini, a local small model), while the main agent runs a more capable model (e.g., Opus, Sonnet, GPT-4). But users can configure any combination — including running both tiers on the same model, or running the gatekeeper locally and the main agent in the cloud.

**The terms "cheap" and "smart" are relative and user-defined.** TUSK doesn't hardcode model tiers — it provides two configurable slots (gatekeeper + main agent) and lets the user decide what goes where.

### 3.4 Intent Detection (Hybrid)

The **gatekeeper model (Tier 1)** performs hybrid intent detection:

- **Name trigger (primary):** Looks for "Tusk" (or configured aliases) in the transcribed text to identify directed commands.
- **Implicit command detection:** Obvious imperative commands (e.g., "open Firefox", "close this window") are caught even without the name trigger, based on phrasing and context.
- **Ambient speech is discarded.** Conversation, background noise, and non-command speech are classified as "not for me" and dropped — they never reach the main agent.

This means: no wake-word button, no "Hey Tusk" ritual. You talk, and if you're talking to TUSK, the gatekeeper catches it and passes it up.

### 3.5 AI Agent Architecture

TUSK is **AI-first**. The core of the application is an AI agent, not a command dispatcher.

- **Main Agent:** The central orchestrator. Consumes environmental context from context-provider extensions, receives classified intents from the gatekeeper, reasons about the user's environment, and emits semantic events (or delegates to sub-agents). Runs on a user-configured LLM (e.g., Claude Opus 4.6, GPT-4, a local model).
- **Sub-Agents:** The main agent can spawn sub-agents for complex, multi-step, or parallel tasks. Each sub-agent can run on a different LLM, chosen for cost, speed, or capability. Sub-agents report back to the main agent.
- **Hot-swappable models:** LLMs are swapped at runtime via voice command. "Tusk, use Sonnet for sub-agents" or "Tusk, switch main agent to local Llama" — the system reconfigures without restart.
- **Master Prompt:** Each agent operates under a configurable master prompt (system prompt) that defines its behavior, safety constraints, and personality. The master prompt is where dangerous action safeguards are defined (see §6.5).

---

## 4. Target Users

**Primary (v1):** Power users and developers on Linux who want faster, hands-free desktop workflows.

**Future:** General desktop users across all major operating systems. The goal is mainstream adoption as the default voice interface layer for desktop computing.

---

## 5. MVP Scope (v1)

### In Scope — Core

| Category | Capabilities |
|---|---|
| **Voice-to-Text Module** | Always-on microphone capture, continuous STT via OpenAI Whisper (swappable) |
| **Tier 1: Gatekeeper Model** | Cheap/fast LLM for continuous intent detection — filters ambient speech, forwards commands |
| **Tier 2: Main AI Agent** | Smart/capable LLM for command understanding (with environmental context), planning, orchestration, event emission |
| **Sub-Agents Subsystem** | Spawn sub-agents for complex/parallel tasks, each on a configurable LLM |
| **Unified Context Schema** | Structured format for environmental state (active windows, focused app, screen layout, etc.) — consumed by the agent, provided by context-provider extensions |
| **LLM Hot-Swap** | Runtime model/provider switching via voice command (e.g., "use Opus 4.6 for main agent") |
| **LLM Providers** | Cloud API to start (Anthropic, OpenAI, OpenRouter, etc.) — provider-configurable per agent |
| **Event System** | Core emits structured semantic events for action-executor extensions; receives structured context from context-provider extensions |
| **Extension API** | Bidirectional extension interface from v1 — supports both context providers and action executors, discovered and loaded at runtime |
| **Safety Layer** | Master prompt with dangerous action definitions, confirmation required for destructive operations |

### In Scope — Extensions (ships with v1)

| Extension | Capabilities |
|---|---|
| **Linux/GNOME Desktop** | **Context provider:** active window, window list/positions/sizes, workspace layout, screen geometry, running applications. **Action executor:** open/close/resize/move/focus windows; launch applications; keyboard key presses; semantic mouse control. First reference extension — not part of the core. |

### Out of Scope (v1)

- Other operating systems (Windows, macOS) — future extensions
- Text-to-speech / voice responses — future core module
- GUI / visual interface for TUSK itself
- Smart home or IoT integration — future extensions
- Mobile platforms

---

## 6. Architecture Principles

1. **AI-first.** The AI agent is not a feature of the app — it *is* the app. The main agent is the central nervous system. Everything flows through it: intent classification, task orchestration, sub-agent management, and event emission. The architecture is designed around the agent, not around a command table.

2. **Core vs. Extensions separation.** The core (voice-to-text, AI agent, sub-agents, event system) knows nothing about specific platforms, applications, or desktop environments. Extensions communicate bidirectionally with the core: **context-provider extensions** push environmental state (active windows, screen layout, running apps) into the agent so it can reason correctly, and **action-executor extensions** receive semantic events and perform platform-specific actions. A single extension can be both. The core consumes a unified context schema and emits a unified event format — the platform-specific translation happens entirely in extensions.

3. **Modularity by design.** Every component — STT engine, gatekeeper model, main agent LLM, extension modules — is a swappable module behind a clean interface. A user can run Whisper locally or swap in Deepgram. They can route the gatekeeper through a local model and the main agent through a cloud API. Nothing is hardwired.

4. **Extension architecture from day one.** Extensibility is not a future feature — it's a v1 requirement. The system exposes an extension API so that users and contributors can add new desktop actions, platform adapters, integrations, and agent behaviors without modifying the core. This is how TUSK grows beyond a single developer and a single platform.

4. **Provider agnosticism.** TUSK does not depend on any single AI provider. It should work with Anthropic, OpenAI, OpenRouter, local models (Ollama, llama.cpp), or any future provider. The LLM layer is a pluggable adapter. Different agents can use different providers simultaneously.

5. **Safety by design.** Voice-controlled desktop actions are powerful and potentially destructive. TUSK defines a set of **dangerous actions** (e.g., mass file deletion, system shutdown, privilege escalation) in the master prompt / system prompt. When a command matches a dangerous action pattern, the system requires explicit confirmation before execution. The master prompt is the single source of truth for safety constraints and is configurable per deployment.

6. **Platform agnosticism (by design, Linux-first by extension).** The core is platform-agnostic by definition — it emits semantic events, not platform calls. Platform support is added by writing extensions. v1 ships with a Linux/GNOME extension. Windows and macOS extensions can be added later without touching the core.

7. **Low latency.** The target latency from spoken command to event emission is **≤ 1 second**. This budget covers STT transcription, Tier 1 gatekeeper classification, Tier 2 main agent processing, and event dispatch. Every architectural decision must respect this constraint. If a component is too slow, it gets optimized or replaced.

8. **Maximum agility.** Lean, fast iteration. No over-engineering. Ship the simplest thing that works, then improve.

---

## 7. Key Technical Decisions

### Language: Python (core) + JavaScript (future GUI)

**Decided.** Python is the language for the core system — STT pipeline, agent orchestration, LLM integration, event system, extension API. Python's ML/audio ecosystem (Whisper, torch, numpy), D-Bus bindings for GNOME, and broad contributor familiarity make it the right choice for v1.

JavaScript/TypeScript will be introduced later if a cross-platform GUI layer is needed (e.g., Electron or Tauri shell). The core remains Python.

### STT: Whisper (swappable)

Start with OpenAI Whisper (local). The STT layer is behind an interface so it can be replaced with Vosk, Deepgram, Azure Speech, or any future engine without touching the rest of the system.

### Two-Tier LLM Architecture

The system uses two distinct LLM tiers, each independently configurable:

**Tier 1 — Gatekeeper (cheap, fast):** Receives all STT output continuously. Its only job is binary classification: *"Is this speech directed at TUSK?"* If yes, it forwards the text (with optional preliminary intent tagging) to Tier 2. If no, it discards. Default: the cheapest available model (e.g., Haiku, GPT-4o-mini, a local small model). Must be fast — its latency eats into the 1-second budget on every single command.

**Tier 2 — Main Agent (smart, capable):** Only receives text that the gatekeeper has classified as a command. Understands the full intent, plans execution, manages sub-agents, and dispatches actions. Default: a capable model (e.g., Claude Opus/Sonnet, GPT-4). Latency matters here too, but the load is much lower since ambient speech never reaches it.

Both tiers are fully configurable — model, provider, local vs. cloud — independently of each other. Users can reconfigure either tier at runtime via voice command. The architecture also supports running both tiers on the same model if a user prefers simplicity over cost optimization.

### LLM Providers: Cloud API (configurable, per-agent)

Start with cloud APIs (Anthropic Claude, OpenAI GPT, OpenRouter, etc.) for both tiers. The system must support configuration so users can choose their provider — including local inference (Ollama, llama.cpp) for fully offline operation. Each agent (gatekeeper, main agent, sub-agents) can be independently configured to use a different LLM and provider.

### Latency Target: ≤ 1 Second

The acceptable end-to-end latency from the end of a spoken command to the beginning of action execution is approximately **1 second**. This is a hard design constraint. The budget is shared across STT transcription, Tier 1 gatekeeper classification, Tier 2 main agent processing, and action dispatch. If a component is too slow, it must be optimized or replaced.

### Safety: Master Prompt + Dangerous Action Registry

Destructive or irreversible actions (e.g., `rm -rf`, system shutdown, mass file operations, privilege escalation) are defined in a **dangerous action registry** within the master prompt / system prompt. When the agent identifies a command that matches a dangerous pattern, it must pause and request explicit voice confirmation before executing. The master prompt is the authoritative source for these safety rules and is configurable by the user/administrator.

---

## 8. Success Criteria for v1

The first milestone is achieved when:

**Core:**
- [ ] TUSK is **always listening** — mic capture and STT run continuously without drops or manual restarts
- [ ] TUSK **always hears** — commands are recognized reliably on the first attempt, no need to repeat
- [ ] The **gatekeeper model (Tier 1)** correctly discards ambient speech and forwards only real commands — the main agent is not invoked on background noise
- [ ] The **main AI agent (Tier 2)** receives classified intents, consumes environmental context, and emits correct semantic events
- [ ] The agent **reasons with context** — commands like "close this window" or "move it to the right" are correctly resolved using environmental state from context-provider extensions
- [ ] **Sub-agents** can be spawned for multi-step tasks
- [ ] **LLM hot-swap** works via voice — "Tusk, use [model] for [agent]" reconfigures the system at runtime
- [ ] Ambient speech is **ignored** — the system doesn't trigger on background conversation or TV audio
- [ ] **Latency is ≤ 1 second** from end of spoken command to event emission
- [ ] **Dangerous actions** trigger a confirmation prompt before event emission
- [ ] The **extension API** is functional and bidirectional — context-provider and action-executor extensions can be loaded without modifying core code
- [ ] The architecture is **modular** — STT, gatekeeper, main agent, and extensions can be swapped via configuration

**Linux/GNOME Desktop Extension:**
- [ ] **Context provider** delivers accurate desktop state — active window, window list, positions, sizes, workspace layout, running apps
- [ ] It **launches applications** by voice (e.g., "Tusk, open Firefox")
- [ ] It **manages windows** — open, close, resize, move, focus (e.g., "move this window to the right half")
- [ ] It **controls mouse and keyboard** — click, type, navigate (e.g., "click the submit button", "type hello world")

---

## 9. Project Meta

| | |
|---|---|
| **Project name** | TUSK — Task Unified Speech Kernel |
| **Assistant persona name** | Tusk (same as project) |
| **License** | Open Source (specific license TBD) |
| **Lead** | Solo developer (founder) |
| **Collaboration model** | Solo to start; designed to attract open-source contributors |
| **Repository** | TBD |
| **Timeline** | No fixed deadline — milestone-driven |

---

## 10. Open Questions

These are unresolved decisions to revisit as development progresses:

1. **License choice** — MIT, Apache 2.0, GPL, or other.
2. **LLM cost management** — the two-tier architecture dramatically reduces main agent invocations, but the gatekeeper still processes every transcribed utterance. At what usage level does a local gatekeeper model become necessary?
3. **Gatekeeper design** — should the gatekeeper return a simple yes/no, or also extract a preliminary intent category to speed up the main agent? How do we measure and tune its false-positive vs. false-negative rate?
4. **Unified context schema design** — what fields belong in the context schema? How frequently should context providers push updates (continuous polling, event-driven, on-demand before each agent invocation)? How do we keep the context payload compact enough to not bloat LLM token usage?
5. **Sub-agent lifecycle** — how long do sub-agents live? Per-task? Per-session? What are the resource limits?
6. **Extension API design** — bidirectionality is decided (context providers + action executors), but: how are extensions discovered, loaded, and sandboxed? What's the registration protocol? Can extensions declare capabilities and required context fields?
7. **Dangerous action list** — what specific operations belong in the dangerous action registry? How granular should it be?
8. **Metrics and telemetry** — what to measure and how (recognition accuracy, gatekeeper precision/recall, command latency breakdown per tier, context freshness, agent response time).
9. **Conversation context** — should the main agent maintain conversational memory within a session? Across sessions?

---

*This document is the starting point. It will evolve as development begins and decisions are made.*
