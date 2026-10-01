# Destructive action confirmation

Last updated: 2026-10-01

## Purpose

Tusk must not close windows, delete content or run shell/kill tools on a misheard or
misrouted command. Such tool calls are held until the user says "Tusk, yes".

## Flow

1. Every real tool call goes through `ConfirmationGate.execute`
   (`tusk/kernel/agent/confirmation/confirmation_gate.py`). Both dispatch points use it:
   `OrchestratorToolDispatcher._traced_execute` and `tool_sequence.Executor._step`.
2. `DestructiveActionPolicy` classifies the call (by name after the adapter prefix):
   `close_window`, tools starting with `kill`, `delete`, `run_shell`, `execute_shell`, `shell`,
   and `press_keys` containing `Delete`, `BackSpace`, `<alt>F4`, `<ctrl>w` or `<ctrl>q`.
   `<ctrl>a` alone only selects and is allowed; the Delete/BackSpace after it is held. Key names are
   compared after splitting on `+`, `<`, `>`, so `Ctrl+W` and `<ctrl>w` are both held.
3. A destructive call is not run. The gate stores one `PendingAction` and returns
   `needs_confirmation: Close window 'X'? Say 'Tusk, yes' to confirm.` A sequence stops at that step.
4. `ConfirmingCommandMode` (wired in `startup.build_api`) replaces the agent's reply with the
   question, so it is spoken. On the next utterance it calls `ConfirmationGate.resolve` first:
   "yes"/"confirm"/"do it" runs the action, "no"/"cancel" replies "Cancelled.", anything else
   drops the action and is routed as a normal command. Actions expire after 30 s.

## Target window check

- The target is `window_title` from the arguments, or else the active window title read via the
  adapter's `*get_active_window` tool. With no target the call is refused outright.
- For calls without `window_title` (key presses, shell tools) the active window is re-read on
  "yes"; if it changed, the action is refused.

## Pitfalls

- The list lives in the kernel to avoid touching `adapters/gnome`; a `destructive` manifest flag
  (read like `settle_ms` in `ToolRegistry._entry`) is the cleaner long-term home.
- Confirmation is handled inside command mode, not ahead of dictation/coding mode slots.
- A bare "yes" never reaches the kernel: the voice `Sanitizer` drops it as an STT ghost phrase and
  the gatekeeper treats a wake-word-less "yes" as ambient. The question therefore asks for "Tusk, yes".
