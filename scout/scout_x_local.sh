#!/usr/bin/env bash
# Launchd-triggered X timeline scraper. Runs Claude Code with Chrome MCP
# against scout/x_scrape_prompt.md. Output goes to ./logs/scout_x.log.
#
# Prereqs (operator-managed, NOT auto-installed):
#   - Chrome MCP server configured in the user's Claude Code settings
#   - Chrome running with an X (twitter.com) session already logged in
#   - `claude` CLI on PATH
#
# Behavior:
#   - Exits 0 even on partial failure (errors logged); launchd never re-fires.
#   - All side effects go through Claude Code: .knowledge.md files emitted at
#     the repo root, copied to kDrive, no wiki ingest (manual).

set -u
set -o pipefail

REPO_ROOT="/Users/shine/videoatexto"
PROMPT_FILE="$REPO_ROOT/scout/x_scrape_prompt.md"
LOG_DIR="$REPO_ROOT/logs"
LOG_FILE="$LOG_DIR/scout_x.log"

mkdir -p "$LOG_DIR"

{
    echo "============================================================"
    echo "scout_x_local.sh start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "============================================================"
} >> "$LOG_FILE"

cd "$REPO_ROOT" || {
    echo "FATAL: cannot cd to $REPO_ROOT" >> "$LOG_FILE"
    exit 0
}

if ! command -v claude >/dev/null 2>&1; then
    echo "FATAL: 'claude' CLI not on PATH" >> "$LOG_FILE"
    exit 0
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "FATAL: prompt file missing at $PROMPT_FILE" >> "$LOG_FILE"
    exit 0
fi

# Pipe the prompt into claude in non-interactive mode. The Chrome MCP server
# is loaded from the operator's standard ~/.claude/settings.json — we do not
# pass --mcp-config here so the global setup is honored.
claude -p "$(cat "$PROMPT_FILE")" \
    --permission-mode bypassPermissions \
    >> "$LOG_FILE" 2>&1

echo "scout_x_local.sh done: $(date -u +%Y-%m-%dT%H:%M:%SZ) (rc=$?)" >> "$LOG_FILE"
exit 0
