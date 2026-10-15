#!/usr/bin/env bash
# Onboard this machine's local AI tools (Claude Code, Codex, ...) onto
# Vaultwarden via the bitwarden MCP server.
#
# Run this once per machine. It prompts you for your Vaultwarden email and
# master password locally (never sent anywhere but the `bw` CLI talking to
# your own Vaultwarden server) and leaves behind:
#   - a saved CLI session so this machine doesn't need the master password
#     again until the session expires or the vault re-locks
#   - a wrapper script MCP clients launch
#   - an attempt to register the MCP server with the local `claude` CLI
#     (prints the manual registration snippet if that CLI isn't present)
#
# Re-run this script any time the saved session goes stale (bw status
# reports "locked") to re-validate and refresh it.
set -euo pipefail

VAULT_SERVER_URL="${VAULT_SERVER_URL:-https://theguylab.duckdns.org/vault}"
INSTALL_DIR="${BITWARDEN_MCP_DIR:-$HOME/.claude/mcp_servers/bitwarden}"

echo "== Bitwarden MCP onboarding =="
echo "Vaultwarden server: $VAULT_SERVER_URL"
echo "Install dir:        $INSTALL_DIR"
echo

command -v bw >/dev/null 2>&1 || { echo "Installing @bitwarden/cli..."; npm install -g @bitwarden/cli; }
command -v mcp-server-bitwarden >/dev/null 2>&1 || { echo "Installing @bitwarden/mcp-server..."; npm install -g @bitwarden/mcp-server; }

mkdir -p "$INSTALL_DIR"
chmod 700 "$INSTALL_DIR"

bw config server "$VAULT_SERVER_URL"

if [ "$(bw login --check 2>&1 | grep -c 'You are logged in')" -eq 0 ]; then
    echo
    echo "Not logged in yet. Enter your Vaultwarden email and master password"
    echo "(this goes straight from your terminal to the bw CLI - nothing here"
    echo "sees or stores it):"
    bw login
fi

echo
echo "Unlocking vault to mint a session token (master password prompt below -"
echo "same guarantee, it never leaves this terminal/CLI exchange):"
SESSION_TOKEN="$(bw unlock --raw)"

ENV_FILE="$INSTALL_DIR/bw_session.env"
printf 'export BW_SESSION=%s\n' "$SESSION_TOKEN" > "$ENV_FILE"
chmod 600 "$ENV_FILE"
echo "Saved session token to $ENV_FILE (mode 600)."

RUN_SCRIPT="$INSTALL_DIR/run.sh"
cat > "$RUN_SCRIPT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

node_major=$(node -p 'Number(process.versions.node.split(".")[0])')
if (( node_major < 20 )); then
  export NODE_OPTIONS="--experimental-global-webcrypto${NODE_OPTIONS:+ $NODE_OPTIONS}"
fi

source "$(dirname "$0")/bw_session.env"
exec mcp-server-bitwarden
EOF
chmod 700 "$RUN_SCRIPT"
echo "Wrote wrapper to $RUN_SCRIPT."

echo
echo "Verifying..."
BW_SESSION="$SESSION_TOKEN" bw status

echo
if command -v claude >/dev/null 2>&1; then
    echo "Registering with the local claude CLI (user scope, all projects)..."
    claude mcp add --scope user bitwarden -- "$RUN_SCRIPT" && echo "Registered." || {
        echo "Automatic registration failed - add this manually to that client's MCP config:"
        echo "  \"bitwarden\": { \"command\": \"$RUN_SCRIPT\" }"
    }
else
    echo "claude CLI not found on PATH. Add this to each local AI tool's MCP config manually:"
    echo "  \"bitwarden\": { \"command\": \"$RUN_SCRIPT\" }"
    echo "(Claude Code: .mcp.json or via 'claude mcp add'. Codex: [mcp_servers.bitwarden] in config.toml"
    echo " with command = \"$RUN_SCRIPT\".)"
fi

echo
echo "Done. This machine's MCP-enabled AI tools can now call bitwarden MCP tools"
echo "directly - no further password entry until the session in $ENV_FILE goes"
echo "stale, at which point just re-run this script."
