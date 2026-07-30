# Source-recovered architecture evidence

## Classification

TUSK is a Python desktop-assistant application structured as an in-process modular core with configurable interaction shells and process-isolated MCP adapters. Deployment also contains an optional Phoenix tracing service and a separate host-side launcher process.

## Hierarchy

1. **TUSK system**
   - Python application container
   - MCP adapter child processes
   - host launcher
   - Phoenix observability service
   - host GNOME/audio environment and external model APIs
2. **Main application process**
   - composition root
   - voice, CLI, emulator, and tray shells
   - kernel and operating modes
   - agent execution engine
   - shared providers and infrastructure
3. **Kernel**
   - `KernelAPI`, `CommandMode`, coding/dictation `ModeSlot`s
   - `ToolRuntime`, `CodingRouter`, `DictationRouter`
   - selectable agent backend
4. **Agent execution**
   - built-in `MainAgent -> AgentOrchestrator -> AgentRuntime`
   - conversation, command, planner, executor, and default profiles
   - optional `codex exec` and persistent `codex mcp-server` backends
5. **Adapters**
   - GNOME desktop control
   - coding edit planning
   - dictation session processing
   - JSON-RPC/MCP over stdio

## Directly supported relationships

- `main.py` builds configuration, tracing, LLM slots, kernel, and shells.
- `ShellLoader` starts selected shells and supplies `KernelAPI.submit`.
- `KernelAPI.submit` serializes requests and routes them to coding, dictation, or command mode.
- `AgentBackendFactory` selects built-in TUSK, `codex_exec`, or `codex_mcp`, with optional built-in fallback.
- `AgentOrchestrator` delegates among agent profiles and dispatches registered tools.
- `AdapterManager` discovers `adapter.json`, starts stdio child processes, performs MCP initialization and tool discovery, and registers proxies.
- Coding and dictation routers call adapter tools and apply changes through the selected desktop adapter.
- The GNOME adapter uses `wmctrl`, `xdotool`, clipboard commands, `xdg-open`, and the host launcher Unix socket.
- `FileStore` persists session events as JSONL.
- `AdapterEnvironmentBuilder` creates versioned adapter virtual environments when required.
- `TracerFactory` exports OTLP traces; Docker Compose routes them to Phoenix.

## Inferred parts

- The overall classification as a modular monolith with process-isolated adapters is inferred from runtime composition and dependency direction rather than a declared architecture label.
- The OpenAI model service behind the Codex binary is inferred; the repository does not contain that network client.
- Some high-level edges aggregate several implementation calls or deployment mounts to avoid low-level noise.

## Summarized or omitted

The map intentionally summarizes DTO/schema classes, prompts, guards, logging helpers, minor utilities, exhaustive tool schemas, test fixtures, E2E harness implementation, and demo-only code. Representative implementation details are shown where exhaustive rendering would damage readability.

## Ambiguities

- The exact network protocol and endpoint used by the external Codex binary cannot be recovered from this repository.
- Runtime shell composition is configuration-dependent; `voice` is the default.
- Codex may start its own manifest-configured adapter processes; the exact lifecycle is partly inside the external binary.
