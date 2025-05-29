import json
import pytest
from llm_tools_mcp import McpConfig, McpClient


@pytest.mark.asyncio
@pytest.mark.online
async def test_streamable_http_postman_echo_mcp():
    """Test streamable HTTP connection to postman-echo-mcp service and list its echoes."""
    mcp_config_content = json.dumps(
        {
            "mcpServers": {
                "postman-echo": {
                    "type": "http",
                    "url": "https://postman-echo-mcp.fly.dev/",
                }
            }
        }
    )

    mcp_config_obj = McpConfig.for_json_content(mcp_config_content)
    mcp_client = McpClient(mcp_config_obj)

    tools = await mcp_client.get_all_tools()

    assert "postman-echo" in tools, "Should have postman-echo server"

    tools = tools.get("postman-echo", [])
    tool_names = [tool.name for tool in tools]

    assert "echo" in tool_names, f"Should have 'echo' tool. Found tools: {tool_names}"

    result = await mcp_client.call_tool(
        "postman-echo", "echo", message="Hello from test!"
    )
    assert result is not None, "Tool call should return a result"
    assert "Hello from test!" in str(result), (
        "Echo result should contain the original message"
    )


@pytest.mark.asyncio
@pytest.mark.online
async def test_sse_deepwiki_mcp():
    """Test SSE connection to deepwiki-mcp service with GitHub-like schema."""
    mcp_config_content = json.dumps(
        {
            "mcpServers": {
                "deepwiki": {"type": "sse", "url": "https://mcp.deepwiki.com/sse"}
            }
        }
    )

    mcp_config_obj = McpConfig.for_json_content(mcp_config_content)
    mcp_client = McpClient(mcp_config_obj)

    tools = await mcp_client.get_all_tools()

    assert "deepwiki" in tools, "Should have deepwiki server"

    tools = tools.get("deepwiki", [])

    result = await mcp_client.call_tool(
        "deepwiki", tools[0].name, repoName="facebook/react"
    )
    assert result is not None, "Tool call should return a result"
    assert "react" in str(result).lower(), "Available pages for facebook/react"


@pytest.mark.asyncio
@pytest.mark.online
async def test_remote_fetch_mcp():
    """Test remote MCP connection to fetch-mcp service for web content fetching."""
    mcp_config_content = json.dumps(
        {
            "mcpServers": {
                "fetch": {
                    "type": "http",
                    "url": "https://remote.mcpservers.org/fetch/mcp",
                }
            }
        }
    )

    mcp_config_obj = McpConfig.for_json_content(mcp_config_content)
    mcp_client = McpClient(mcp_config_obj)

    tools = await mcp_client.get_all_tools()

    assert "fetch" in tools, "Should have fetch server"

    tools = tools.get("fetch", [])
    tool_names = [tool.name for tool in tools]

    assert "fetch" in tool_names, (
        f"Should have a fetching tool. Found tools: {tool_names}"
    )
