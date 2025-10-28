import asyncio
import llm
import mcp


from llm_tools_mcp.defaults import DEFAULT_MCP_JSON_PATH
from llm_tools_mcp.mcp_config import McpConfig
from llm_tools_mcp.mcp_client import McpClient


def _create_tool_for_mcp(
    server_name: str, mcp_client: McpClient, mcp_tool: mcp.Tool
) -> llm.Tool:
    def impl(**kwargs):
        return asyncio.run(mcp_client.call_tool(server_name, mcp_tool.name, **kwargs))

    enriched_description = mcp_tool.description or ""
    enriched_description += f"\n[from MCP server: {server_name}]"

    return llm.Tool(
        name=mcp_tool.name,
        description=enriched_description,
        input_schema=mcp_tool.inputSchema,
        plugin="llm-tools-mcp",
        implementation=impl,
    )


def _get_tools_for_llm(mcp_client: McpClient) -> list[llm.Tool]:
    tools = asyncio.run(mcp_client.get_all_tools())
    mapped_tools: list[llm.Tool] = []
    for server_name, server_tools in tools.items():
        for tool in server_tools:
            mapped_tools.append(_create_tool_for_mcp(server_name, mcp_client, tool))
    return mapped_tools


class MCP(llm.Toolbox):
    def __init__(self, config_path: str = DEFAULT_MCP_JSON_PATH):
        mcp_config = McpConfig.for_file_path(config_path)
        mcp_client = McpClient(mcp_config)
        computed_tools = _get_tools_for_llm(mcp_client)

        for tool in computed_tools:
            self.add_tool(tool, pass_self=True)


@llm.hookimpl
def register_tools(register):
    register(MCP)
