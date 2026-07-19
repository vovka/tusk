# Editor Driver Seam — from GUI automation to editor-native

`CodingRouter` doesn't change. Growth happens in the adapter (targeted operations from a
diff step) and below the `EditorDriver` ABC (a bridge driver that makes read-back and
drift resync cheap). Green = exists, yellow = new.

```mermaid
flowchart TD
    U[utterance] --> CR[CodingRouter ✓]
    CR -->|process_intent| CAD["coding adapter ✓<br/>BufferModel + CodingEditPlanner"]
    CAD -->|"EditOperation(s)"| CR
    TS["tree-sitter symbol map (new)<br/>grounds 'delete this function'"] -.-> CAD
    DIF["edit-operation differ (new)<br/>difflib → targeted per-range ops"] -.-> CAD

    CR --> VS["VerifiedEditStrategy ✓ wired<br/>line-anchored apply → read-back →<br/>full-replace repair on drift"]

    VS --> DRV{EditorDriver}
    DRV -->|universal fallback| IA["InputAutomationEditorDriver ✓<br/>gnome.* keys + clipboard<br/>fire-and-forget"]
    DRV -->|focused window = VS Code| VSD["VsCodeEditorDriver (new)"]

    IA --> GA[gnome adapter ✓ → any editor]
    VSD --> EXT["VS Code extension (new)<br/>read_buffer / apply_edit / cursor<br/>local socket"]

    EXT -.->|read_buffer| SYNC["drift resync (new)<br/>refresh BufferModel"]
    SYNC -.-> CAD

    style TS fill:#fdf3d8,stroke:#b90
    style DIF fill:#fdf3d8,stroke:#b90
    style VSD fill:#fdf3d8,stroke:#b90
    style EXT fill:#fdf3d8,stroke:#b90
    style SYNC fill:#fdf3d8,stroke:#b90
```

Driver choice happens once per session — focused window class + bridge ping
(`DriverSelector` in the wiring, `TUSK_CODING_DRIVER` override). The strategy chain is
unchanged; the bridge driver just makes its read-back verification a cheap socket call
instead of a clipboard round-trip. No new layer.
