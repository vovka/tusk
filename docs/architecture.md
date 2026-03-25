# TUSK — Current Architecture

## Layers

TUSK is split into three layers:

1. `tusk/kernel/`
   Handles STT, gatekeeping, the main agent loop, conversation history, model registry, tool registry, and adapter lifecycle.
2. `shells/`
   User-facing entrypoints. `shells/voice` owns microphone capture and VAD. `shells/cli` is a direct text shell for development and testing.
3. `adapters/`
   MCP servers discovered from `adapters/*/adapter.json`. `adapters/gnome` provides desktop context and desktop-control tools. `adapters/dictation` owns dictation cleanup/refinement sessions.

## Runtime Flow

### Voice shell

`AudioCapture` -> `UtteranceDetector` -> `KernelAPI.submit_utterance()` -> STT -> gatekeeper -> main agent -> tool call -> MCP adapter

### CLI shell

stdin -> `KernelAPI.submit_text()` -> main agent -> tool call -> MCP adapter

`submit_text()` bypasses STT and gatekeeping. It is treated as a direct command path.

## Adapter Model

- Adapters are started from `adapter.json`.
- Tool names are registered as `adapter_name.tool_name`.
- The kernel uses stdio JSON-RPC for v1.
- `AdapterManager` can watch `adapters/` for hot-plug and tries shared-env startup first, then a managed env under `.tusk_runtime/adapters/` if needed.
- Exactly one context-providing desktop adapter is used at a time.

## Dictation

- `start_dictation` remains a kernel orchestration tool.
- The kernel starts a session in `adapters/dictation`.
- While dictation is active, the kernel bypasses gatekeeping and forwards transcript chunks to the dictation adapter.
- The dictation adapter returns edit operations.
- The kernel applies those edits through the active desktop adapter (`type_text`, `replace_recent_text`).

## Key Files

- `main.py`
- `tusk/kernel/api.py`
- `tusk/kernel/adapter_manager.py`
- `tusk/kernel/mcp_client.py`
- `adapters/gnome/server.py`
- `adapters/dictation/server.py`

## Current Gaps

- HTTP MCP transport is not implemented yet.
- Dangerous-action confirmation is still out of scope.
- Cross-session memory is still out of scope.
