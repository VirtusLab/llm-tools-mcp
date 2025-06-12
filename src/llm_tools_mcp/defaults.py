import os


DEFAULT_CONFIG_DIR = os.environ.get("LLM_TOOLS_MCP_CONFIG_DIR", "~/.llm-tools-mcp")
DEFAULT_MCP_JSON_PATH = os.path.join(DEFAULT_CONFIG_DIR, "mcp.json")
