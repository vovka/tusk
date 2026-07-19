# Editor Driver Seam — from GUI automation to editor-native

`CodingRouter` and the coding adapter don't change. Growth happens below the two ABCs:
a feedback-capable driver unlocks the dormant line-anchored strategy and automatic drift
resync. Green = exists, yellow = new.

```mermaid
flowchart TD
    U[utterance] --> CR[CodingRouter ✓]
    CR -->|process_intent| CAD["coding adapter ✓<br/>BufferModel + CodingEditPlanner"]
    CAD -->|"EditOperation(s)"| CR
    TS["tree-sitter symbol map (new)<br/>grounds 'delete this function'"] -.-> CAD

    CR --> STRAT{EditApplicationStrategy}
    STRAT -->|"driver w/o readback"| FR[FullReplaceEditStrategy ✓<br/>select-all + paste full_buffer]
    STRAT -->|"driver w/ readback"| LA["LineAnchoredEditStrategy<br/>✓ exists, unwired"]

    FR --> DRV{EditorDriver}
    LA --> DRV
    DRV -->|universal fallback| IA["InputAutomationEditorDriver ✓<br/>gnome.* keys + clipboard<br/>fire-and-forget"]
    DRV -->|focused window = VS Code| VSD["VsCodeEditorDriver (new)"]

    IA --> GA[gnome adapter ✓ → any editor]
    VSD --> EXT["VS Code extension (new)<br/>read_buffer / apply_edit / cursor<br/>local socket"]

    EXT -.->|read_buffer| SYNC["drift resync (new)<br/>refresh BufferModel"]
    SYNC -.-> CAD

    style TS fill:#fdf3d8,stroke:#b90
    style VSD fill:#fdf3d8,stroke:#b90
    style EXT fill:#fdf3d8,stroke:#b90
    style SYNC fill:#fdf3d8,stroke:#b90
    style LA fill:#e8f4e8,stroke:#2a7,stroke-dasharray: 5 5
```

Strategy choice becomes a function of driver capability (`supports_readback`), wired in
`ToolRuntime`; driver choice a function of the focused window class. Both decisions live in
existing wiring code — no new layer.
