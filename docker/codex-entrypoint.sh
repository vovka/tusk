#!/bin/sh
# Prepare a container-local codex home so codex-in-container uses the in-container
# gnome adapter without polluting the host's ~/.codex/config.toml. Auth is copied
# from the read-only host mount; DISPLAY/XAUTHORITY are templated from the
# container env so the gnome MCP server can reach the host desktop.
set -e

CODEX_HOME="${CODEX_HOME:-/tmp/.codex}"
mkdir -p "$CODEX_HOME"
[ -f /host-codex/auth.json ] && cp /host-codex/auth.json "$CODEX_HOME/auth.json" || true

cat > "$CODEX_HOME/config.toml" <<EOF
model = "${CODEX_EXEC_MODEL:-gpt-5.5}"
model_reasoning_effort = "${CODEX_REASONING_EFFORT:-low}"

[projects."/app"]
trust_level = "trusted"

EOF
# MCP servers come from the same adapters/*/adapter.json manifests TUSK loads,
# so codex always sees the same adapter set as the kernel.
python3 /app/tools/codex_mcp_config_generator.py /app/adapters >> "$CODEX_HOME/config.toml"

exec "$@"
