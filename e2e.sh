#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
    if [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
    if [ -n "${MCP_CONFIG_DIR:-}" ] && [ -d "$MCP_CONFIG_DIR" ]; then
        rm -rf "$MCP_CONFIG_DIR"
    fi
}

trap cleanup EXIT

TEMP_DIR=$(mktemp -d ./e2e-testtmp.XXXXXX)
TEST_DIR="$TEMP_DIR/demo_files"
MCP_CONFIG_DIR="$TEMP_DIR/.llm-tools-mcp"

mkdir -p "$TEST_DIR"
echo "Hello, world!" > "$TEST_DIR/hello.txt"

mkdir -p "$MCP_CONFIG_DIR"

cat > "$MCP_CONFIG_DIR/mcp.json" << EOF
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem@2025.3.28",
        "$TEST_DIR"
      ]
    }
  }
}
EOF

export LLM_TOOLS_MCP_CONFIG_DIR="$MCP_CONFIG_DIR"

echo "Installing LLM and plugins..."
if ! command -v uv &> /dev/null; then
    echo "⚠️ ERROR: uv is not installed. Please install uv first."
    exit 1
fi

uv tool install llm
llm install $SCRIPT_DIR
llm install llm-echo==0.3a3


TOOLS_OUTPUT=$(llm tools list 2>&1 || true)
if echo "$TOOLS_OUTPUT" | grep -q "read_file"; then
    echo "MCP tools are available"
else
    echo "🛑 ERROR: MCP are not available"
fi

SIMPLE_TEST='{"tool_calls": [{"name": "list_directory", "arguments": {"path": "'$TEST_DIR'"}}], "prompt": "List files in current directory"}'
SIMPLE_OUTPUT=$(llm -m echo -T MCP "$SIMPLE_TEST" 2>&1)
if [ $? -ne 0 ]; then
    echo "🛑 ERROR: Simple MCP test failed: $SIMPLE_OUTPUT"
    exit 1
fi


if ! echo "$SIMPLE_OUTPUT" | grep -q "hello.txt"; then
    echo "🛑 ERROR: Simple test output doesn't contain expected tool_calls: $SIMPLE_OUTPUT"
    exit 1
fi

TEST_PROMPT='{"tool_calls": [{"name": "read_file", "arguments": {"path": "'$TEST_DIR'/hello.txt"}}], "prompt": "Read the hello.txt file"}'
MCP_ECHO_OUTPUT=$(llm -m echo -T MCP "$TEST_PROMPT" 2>&1)
if [ $? -ne 0 ]; then
    echo "🛑 ERROR: MCP echo test failed: $MCP_ECHO_OUTPUT"
    exit 1
fi
if ! echo "$MCP_ECHO_OUTPUT" | grep -q "Hello, world!2"; then
    echo "🛑 ERROR: Echo output doesn't contain expected tool_calls: $MCP_ECHO_OUTPUT"
    exit 1
fi


echo "✅ End-to-end test completed successfully!"
