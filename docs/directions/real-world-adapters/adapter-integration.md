# Third-Party MCP Server Integration Path

A wrapped server is a directory with a hand-written `adapter.json` and no code. Green =
exists, yellow = new. The approval gate comes from the approvals direction.

```mermaid
flowchart TD
    subgraph "adapters/gmail/ (new, manifest only)"
        M["adapter.json<br/>entry: npx -y mcp-server-gmail<br/>tools: send_message → requires_approval<br/>noisy tools → planner_visible=false"]
    end

    M --> AM[AdapterManager ✓<br/>discovery + hot-plug]
    AM --> EB[AdapterEnvironmentBuilder]
    EB -->|"requirements.txt ✓"| VENV[managed venv ✓]
    EB -->|"package.json (new)"| NPM["npm install path (new)<br/>Node/uv in image (new)"]
    EB -->|"env = os.environ ✓"| SECRETS[".env API keys / token paths<br/>reach the subprocess today"]

    AM --> C[MCPClient ✓ stdio JSON-RPC]
    C -->|"initialize / tools/list / tools/call"| SRV["third-party MCP server<br/>(npm / uvx / python)"]
    C --> HARD["dialect hardening (new):<br/>multi-part content, notifications,<br/>capability negotiation"]

    SRV --> TOK["OAuth tokens<br/>one-time host-side bootstrap (new)<br/>→ mounted volume"]

    C --> PX[MCPToolProxy ✓ → ToolResult]
    PX --> REG[ToolRegistry ✓<br/>gmail.send_message, calendar.create_event, …]
    REG --> PLN[planner catalog ✓ — scales by per-task selection]
    REG --> GATE["approval gate<br/>(approvals direction)"]

    style NPM fill:#fdf3d8,stroke:#b90
    style HARD fill:#fdf3d8,stroke:#b90
    style TOK fill:#fdf3d8,stroke:#b90
    style GATE fill:#fdf3d8,stroke:#b90,stroke-dasharray: 5 5
```
