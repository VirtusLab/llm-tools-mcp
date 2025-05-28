import llm
import mcp

import asyncio


from pathlib import Path
from typing import Dict, List, Optional
import llm
import json
from mcp import (
    ClientSession,
    ListToolsResult,
    StdioServerParameters,
    stdio_client,
    Tool,
)
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    command: str = Field()
    args: Optional[List[str]] = Field(default=None)
    env: Optional[Dict[str, str]] = Field(default=None)


class McpConfigType(BaseModel):
    mcpServers: Dict[str, ServerConfig]


class McpConfig:
    def __init__(self, path="~/.llm-tools-mcp/mcp.json"):
        config_file_path = Path(path).expanduser()
        with open(config_file_path) as config_file:
            unparsed_config = config_file.read()
            config = json.loads(unparsed_config)

            self.config: McpConfigType = McpConfigType(**config)

    def get(self) -> McpConfigType:
        return self.config


class McpClient:
    def __init__(self, config: McpConfig):
        self.config = config

    def server_params_for(self, name: str):
        server_config = self.config.get().mcpServers.get(name)
        if not server_config:
            raise ValueError(f"There is no such MCP server: {name}")
        return StdioServerParameters(
            command=server_config.command,
            args=server_config.args or [],
            env=server_config.env,
        )

    async def get_tools_for(self, name: str) -> ListToolsResult:
        params = self.server_params_for(name)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                return await session.list_tools()

    async def get_all_tools(self) -> Dict[str, List[Tool]]:
        out: Dict[str, List[Tool]] = dict()
        for server_name, server_config in self.config.get().mcpServers.items():
            tools = await self.get_tools_for(server_name)
            out[server_name] = tools.tools
        return out

    async def call_tool(self, server_name: str, name: str, **kwargs):
        params = self.server_params_for(server_name)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                returned = await session.call_tool(name, kwargs)
                return returned.content


def create_tool_for_mcp(
    server_name: str, mcp_client: McpClient, mcp_tool: mcp.Tool
) -> llm.Tool:
    def impl(**kwargs):
        return asyncio.run(mcp_client.call_tool(server_name, mcp_tool.name, **kwargs))

    return llm.Tool(
        name=mcp_tool.name,
        description=mcp_tool.description,
        input_schema=mcp_tool.inputSchema,
        plugin="llm-tools-mcp",
        implementation=impl,
    )


@llm.hookimpl
def register_tools(register):
    mcp_config = McpConfig()
    mcp_client = McpClient(mcp_config)
    for server_name, tools in asyncio.run(mcp_client.get_all_tools()).items():
        for tool in tools:
            register(create_tool_for_mcp(server_name, mcp_client, tool))
