# Approval Flow — awaiting_approval as a turn boundary

The executor never blocks waiting for the user. Hitting a `requires_approval` tool ends the
run with a persisted session; the confirmation arrives as a *new* `submit()` call consumed
by `PendingApprovalSlot`, which resumes the persisted executor session on "yes".

```mermaid
sequenceDiagram
    participant U as User (voice)
    participant K as KernelAPI
    participant CM as CommandMode
    participant RT as AgentRuntime (executor)
    participant TR as ToolRegistry
    participant SS as Session Store
    participant PA as PendingApprovalSlot
    participant TTS as TTS

    U->>K: "send the reply to Anna"
    K->>CM: submit → agent turn
    CM->>RT: run(executor, tools)
    RT->>TR: next tool: email.send_message
    Note over RT,TR: RegisteredTool.requires_approval = true
    RT->>SS: persist pending call + full message history
    RT-->>CM: AgentResult(status="awaiting_approval")
    CM->>PA: arm(session_id, pending_call)
    CM->>TTS: "Send this email to Anna — yes or no?"

    U->>K: "yes"
    Note over K,PA: PendingApprovalSlot is checked before ModeSlots and CommandMode
    K->>PA: consume utterance
    PA->>PA: yes/no classify (gatekeeper LLM slot)
    alt approved
        PA->>CM: resume(session_id)
        CM->>RT: re-enter executor with session_refs
        RT->>TR: execute email.send_message
        TR-->>RT: ToolResult(success)
        RT-->>CM: AgentResult(done)
        CM->>TTS: "Sent."
    else declined / unclear
        PA->>SS: mark cancelled (audit event)
        PA->>TTS: "Cancelled."
    end
```
