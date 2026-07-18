# Direction: "Actually Does Things" Adapters (email, calendar, notes, reminders)

**Research basis:** the most-cited concrete ask in mainstream threads — a desktop AI that
reads Gmail, adds calendar events, keeps reminders and notes, and executes instead of
chatting (r/ChatGPT, r/WindowsHelp, r/opensource)
([market research](../../market-research-reddit-2026-07.md)).
**Verdict:** this is what the adapter layer was built for — TUSK already speaks MCP over
stdio with manifest discovery and hot-plug. The real risk is dialect compatibility with
third-party MCP servers, not architecture. The first wrapped server will surface every gap
cheaply; approvals (separate direction) are a prerequisite for enabling send/delete tools.

**Diagram:** [third-party adapter integration path](adapter-integration.md)

## What the architecture already provides

- **The adapter model is MCP.** `adapter.json` → spawn stdio server → `initialize` →
  `tools/list` → registered as `MCPToolProxy`. The manifest `entry` is any shell command —
  `npx -y <mcp-server>` is a valid entry today.
- **Secrets already flow.** `AdapterEnvironmentBuilder.base_env()` copies the full container
  environment — API keys set in `.env` reach adapter subprocesses with zero new plumbing.
- **Scale-by-design tool catalog.** The planner receives a compact name+description catalog
  and selects per task, so adding 30 PIM tools does not bloat executor prompts — this is the
  documented low-latency design working in our favor.
- **Result mapping is standard-shaped.** `MCPToolProxy` converts `is_error`/content →
  `ToolResult`; no tusk-specific result convention is imposed on adapters.
- **Python dependency isolation.** `requirements.txt` → managed venv per adapter version.

## Gaps

- **Minimal MCP dialect.** `MCPClient` implements line-delimited JSON-RPC with
  `initialize`/`tools/list`/`tools/call` and `MCPToolResult.content` as a single string.
  Real-world servers send multi-part/typed content arrays, notifications, capability
  negotiation, sometimes resources/prompts. Tolerance is unverified.
- **No Node/uvx runtime.** The Docker image has Python only; most popular MCP servers are
  npm or uvx packages. No npm equivalent of the venv builder.
- **No HTTP/SSE transport.** `connect_http()` raises `NotImplementedError` — hosted/remote
  MCP servers are unreachable (fine to defer; stdio covers the popular ones).
- **OAuth bootstrap.** Gmail/Calendar need a one-time browser consent flow and token
  refresh — the container has no browser and no token store.
- **Safety coupling.** `send_message`/`delete_event` must not ship before the
  approvals direction lands (`requires_approval` flags in the wrapping manifests).

## Required changes

1. **[shared/mcp]** Harden `MCPClient`/`MCPToolResult` against spec-compliant servers:
   join multi-part text content, ignore notifications, tolerate unknown capabilities.
   Test against 2–3 popular OSS servers and fix what breaks — cheapest discovery path.
2. **[docker]** Add Node (and `uv`) to the image; extend `AdapterEnvironmentBuilder` with a
   `package.json` → `npm install` path mirroring the venv pattern.
3. **[new adapters]** Thin manifest wrappers for chosen servers (start: one email, one
   calendar), declaring per-tool `planner_visible`/`requires_approval` flags. Decision per
   integration: wrap an existing OSS server vs. write a tusk-native adapter — wrap first,
   go native only where wrapped quality disappoints.
4. **[host/docs]** OAuth bootstrap: a one-time host-side auth script writing token files
   into a mounted volume (the codex-auth copy in `docker/codex-entrypoint.sh` is the
   precedent), refresh handled by the wrapped server itself.
5. **[deferred]** HTTP/SSE transport — only when a concretely needed server has no stdio
   distribution.

## Risks & notes

- Third-party server quality varies; the manifest wrapper gives a curation point (hide noisy
  tools via `planner_visible=false`) without forking upstream.
- Codex backends see the same manifests via the config generator — wrapped servers reach
  codex too; its `read-only` default sandbox is the safety net there.
- Prompt-injection surface grows with email content entering agent context; keep the
  conversation agent's context to planner/executor summaries (already the design) and
  revisit when read-email tools land.
