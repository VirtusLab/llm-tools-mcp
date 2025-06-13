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


def _create_tool_for_mcp_introspection(tool: llm.Tool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "arguments": tool.input_schema,
        "implementation": lambda: "dummy",
    }


def _get_tools_for_llm(mcp_client: McpClient) -> list[llm.Tool]:
    tools = asyncio.run(mcp_client.get_all_tools())
    mapped_tools: list[llm.Tool] = []
    for server_name, server_tools in tools.items():
        for tool in server_tools:
            mapped_tools.append(_create_tool_for_mcp(server_name, mcp_client, tool))
    return mapped_tools


def _get_tools_for_llm_introspection(tools: list[llm.Tool]) -> list[dict]:
    return [_create_tool_for_mcp_introspection(tool) for tool in tools]


@llm.hookimpl
def register_tools(register):
    mcp_config: McpConfig | None = None
    mcp_client: McpClient | None = None
    tools: list[llm.Tool] | None = None

    def compute_tools(config_path: str = DEFAULT_MCP_JSON_PATH) -> list[llm.Tool]:
        nonlocal tools
        nonlocal mcp_config
        nonlocal mcp_client
        previous_config = mcp_config.get() if mcp_config else None
        new_mcp_config = McpConfig.for_file_path(config_path)
        if mcp_client is None or new_mcp_config.get() != previous_config:
            if mcp_client is not None:
                asyncio.run(mcp_client.close())
            mcp_client = McpClient(new_mcp_config)
            mcp_config = new_mcp_config
            tools = _get_tools_for_llm(mcp_client)
        else:
            if tools is None:
                tools = _get_tools_for_llm(mcp_client)
        return tools

    class MCP(llm.Toolbox):
        def __init__(self, config_path: str = DEFAULT_MCP_JSON_PATH):
            self.config_path = config_path

        def method_tools(self):
            tools = compute_tools(self.config_path)
            yield from iter(tools) if tools else iter([])

        @classmethod
        def introspect_methods(cls):
            tools = compute_tools()
            return _get_tools_for_llm_introspection(tools) if tools else []

    register(MCP)
