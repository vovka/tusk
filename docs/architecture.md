# TUSK — Current Architecture

## Layers

TUSK is split into three layers:

1. `tusk/kernel/`
   Handles STT, gatekeeping, the main agent loop, conversation history, model registry, tool registry, and adapter lifecycle.
2. `shells/`
   User-facing entrypoints. `shells/voice` owns microphone capture and VAD. `shells/cli` is a direct text shell for development and testing.
3. `adapters/`
   MCP servers discovered from `adapters/*/adapter.json`. `adapters/gnome` provides desktop context and desktop-control tools. `adapters/dictation` owns dictation cleanup/refinement sessions.

## Agent Prompt Strategy

- The main agent no longer receives an automatic desktop-context message.
- The system prompt no longer contains the full tool registry or full JSON schemas for every tool.
- The agent uses provider-native tool calling instead of prompt-encoded JSON tool instructions.
- Every agent request exposes three broker tools as native tool definitions: `find_tools`, `describe_tool`, and `run_tool`.
- On startup, the kernel reads `.tusk_runtime/tool_usage.json` and injects the top 3 currently available real tools as direct-call tools for the session.
- Tool usage ranking is success-based and recency-weighted, so the direct-call set adapts over time without growing the prompt.
- All other tools stay hidden from the prompt and are reachable only through `run_tool`.

## Runtime Flow

### Voice shell

`AudioCapture` -> `UtteranceDetector` -> `KernelAPI.submit_utterance()` -> STT -> gatekeeper -> main agent -> tool call -> MCP adapter

### CLI shell

stdin -> `KernelAPI.submit_text()` -> main agent -> tool call -> MCP adapter

`submit_text()` bypasses STT and gatekeeping. It is treated as a direct command path.

When the agent needs a hidden tool, the runtime flow is:

`command` -> `find_tools` -> optional `describe_tool` -> `run_tool` -> real tool

When the agent uses a real tool, the loop continues through native tool-call messages:

`assistant tool_call` -> `tool result` -> next native tool_call or `done`

When a real tool succeeds, the kernel updates the persistent usage file. Broker-tool calls themselves are never counted.

## Adapter Model

- Adapters are started from `adapter.json`.
- Tool names are registered as `adapter_name.tool_name`.
- The kernel uses stdio JSON-RPC for v1.
- `AdapterManager` can watch `adapters/` for hot-plug and tries shared-env startup first, then a managed env under `.tusk_runtime/adapters/` if needed.
- Exactly one context-providing desktop adapter is used at a time.
- Desktop inspection tools still exist in the GNOME adapter, but they are fetched on demand rather than injected automatically into the agent prompt.

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
