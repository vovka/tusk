# Profile Layering — a vertical is an env preset

No new config system: a profile is an env file layered under the user's `.env` via
standard compose `env_file` ordering. The only code change is the `TUSK_ADAPTERS` filter
(yellow).

```mermaid
flowchart TD
    subgraph "profiles/ (new, plain env files)"
        P1[coding.env<br/>TUSK_ADAPTERS=gnome,coding<br/>stronger executor model]
        P2[dictation.env<br/>TUSK_ADAPTERS=gnome,dictation<br/>TUSK_ACK=off]
        P3[accessibility.env<br/>all adapters, ack on,<br/>conservative approvals]
        P4[local-private.env<br/>local/* slots, whisper, piper<br/>from local-profile direction]
    end

    P1 & P2 & P3 & P4 --> EF["compose env_file layering:<br/>[profiles/&lt;name&gt;.env, .env]<br/>user .env wins"]
    EF --> CF[ConfigFactory ✓ → frozen Config]

    CF --> SH["ShellLoader ✓<br/>TUSK_SHELLS"]
    CF --> LR["LLMRegistry ✓<br/>per-slot models"]
    CF --> SE["STT/TTS factories ✓/new"]
    CF --> AD["AdapterManager<br/>TUSK_ADAPTERS filter (new)"]

    AD --> A1[gnome ✓]
    AD --> A2[dictation ✓]
    AD --> A3[coding ✓]
    AD --> A4["PIM adapters<br/>(real-world-adapters direction)"]

    AD -.->|same variable| CX["codex config generator ✓<br/>must respect the filter"]

    GT["guardrail test (new):<br/>every profiles/*.env loads through<br/>ConfigFactory, no unknown keys"] -.-> EF

    style AD fill:#fdf3d8,stroke:#b90
    style GT fill:#fdf3d8,stroke:#b90
    style P1 fill:#fdf3d8,stroke:#b90
    style P2 fill:#fdf3d8,stroke:#b90
    style P3 fill:#fdf3d8,stroke:#b90
    style P4 fill:#fdf3d8,stroke:#b90
```
