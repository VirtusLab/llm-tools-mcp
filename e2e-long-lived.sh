#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_SCRIPT="$SCRIPT_DIR/test_servers/connection_counter.py"

cleanup() {
    if [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
    if [ -n "${MCP_CONFIG_DIR:-}" ] && [ -d "$MCP_CONFIG_DIR" ]; then
        rm -rf "$MCP_CONFIG_DIR"
    fi
}

trap cleanup EXIT

TEMP_DIR=$(mktemp -d ./e2e-long-lived.XXXXXX)
MCP_CONFIG_DIR="$TEMP_DIR/.llm-tools-mcp"
EVENT_FILE1="$TEMP_DIR/events1.json"
EVENT_FILE2="$TEMP_DIR/events2.json"

mkdir -p "$MCP_CONFIG_DIR"

cat > "$MCP_CONFIG_DIR/mcp.json" << JSONEOF
{
  "mcpServers": {
    "first": {
      "command": "$SERVER_SCRIPT",
      "args": ["--output", "$EVENT_FILE1", "--tool-description", "first"]
    },
    "second": {
      "command": "$SERVER_SCRIPT",
      "args": ["--output", "$EVENT_FILE2", "--tool-description", "second"]
    }
  }
}
JSONEOF

export LLM_TOOLS_MCP_CONFIG_DIR="$MCP_CONFIG_DIR"

if ! command -v uv &> /dev/null; then
    echo "⚠️ ERROR: uv is not installed. Please install uv first."
    exit 1
fi

uv tool install llm
llm install "$SCRIPT_DIR"
llm install llm-echo==0.3a3

llm tools list > /dev/null

PROMPT='{"tool_calls": [{"name": "dummy"}, {"name": "dummy_1"}], "prompt": "run"}'
llm -m echo -T MCP "$PROMPT" > /dev/null

count1=$(jq length "$EVENT_FILE1")
count2=$(jq length "$EVENT_FILE2")

if [ $((count1 % 2)) -ne 0 ] || [ $((count2 % 2)) -ne 0 ] || [ "$count1" -lt 4 ] || [ "$count2" -lt 4 ]; then
    echo "🛑 ERROR: Unexpected connection counts: first=$count1 second=$count2"
    exit 1
fi

echo "✅ Long-lived e2e test passed"

