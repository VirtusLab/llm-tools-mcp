from contextlib import asynccontextmanager
import asyncio
import datetime
import uuid
import llm
import mcp
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.sse import sse_client
from pathlib import Path
from typing import Annotated, Dict, List, Optional, TextIO, Union
from pydantic import Discriminator, BaseModel, Field, Tag
import json

from mcp import (
    ClientSession,
    ListToolsResult,
    StdioServerParameters,
    stdio_client,
    Tool,
)


def get_discriminator_value(v: dict) -> str:
    if "type" in v:
        type_value = v["type"]
        if isinstance(type_value, str):
            allowed_types = ["stdio", "sse", "http"]
            if type_value in allowed_types:
                return type_value
            else:
                raise ValueError(
                    f"Unknown server 'type'. Provided 'type': ${type_value}. Allowed types: ${allowed_types}"
                )
        else:
            raise ValueError(
                f"Server 'type' should be string. Provided 'type': {type_value}"
            )

    else:
        if "url" in v and "command" in v:
            raise ValueError(
                f"Only 'url' or 'command' is allowed, not both. Provided 'url': {v['url']}, provided 'command': {v['command']}"
            )
        if "url" in v:
            return "sse"
        elif "command" in v:
            return "stdio"
        else:
            raise ValueError(
                "Could not deduce MCP server type. Provide 'url' or 'command'. You can explicitly specify the type with 'type' field."
            )


class StdioServerConfig(BaseModel):
    command: str = Field()
    args: Optional[List[str]] = Field(default=None)
    env: Optional[Dict[str, str]] = Field(default=None)


class SseServerConfig(BaseModel):
    url: str = Field()


class HttpServerConfig(BaseModel):
    url: str = Field()


StdioOrSseServerConfig = Annotated[
    Union[
        Annotated[StdioServerConfig, Tag("stdio")],
        Annotated[HttpServerConfig, Tag("http")],
        Annotated[SseServerConfig, Tag("sse")],
    ],
    Discriminator(get_discriminator_value),
]


class McpConfigType(BaseModel):
    mcpServers: Dict[str, StdioOrSseServerConfig]


class McpConfig:
    def __init__(
        self, config: McpConfigType, log_path: Path = Path("~/.llm-tools-mcp/logs")
    ):
        self.config = config
        self.log_path = log_path.expanduser()

    @classmethod
    def for_file_path(cls, path: str = "~/.llm-tools-mcp/mcp.json"):
        config_file_path = Path(path).expanduser()
        with open(config_file_path) as config_file:
            return cls.for_json_content(config_file.read())

    @classmethod
    def for_json_content(cls, content: str):
        McpConfigType.model_validate_json(content)
        config = json.loads(content)
        config_validated: McpConfigType = McpConfigType(**config)
        return cls(config_validated)

    def with_log_path(self, log_path: Path):
        return McpConfig(self.config, log_path)

    def get(self) -> McpConfigType:
        return self.config


class McpClient:
    def __init__(self, config: McpConfig):
        self.config = config

    @asynccontextmanager
    async def _client_session(self, name: str):
        server_config = self.config.get().mcpServers.get(name)
        if not server_config:
            raise ValueError(f"There is no such MCP server: {name}")
        if isinstance(server_config, SseServerConfig):
            async with sse_client(server_config.url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
        elif isinstance(server_config, HttpServerConfig):
            async with streamablehttp_client(server_config.url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
        elif isinstance(server_config, StdioServerConfig):
            params = StdioServerParameters(
                command=server_config.command,
                args=server_config.args or [],
                env=server_config.env,
            )
            log_file = self._log_file_for_session(name)
            async with stdio_client(params, errlog=log_file) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
        else:
            raise ValueError(f"Unknown server config type: {type(server_config)}")

    def _log_file_for_session(self, name: str) -> TextIO:
        log_file = (
            self.config.log_path.parent
            / "logs"
            / f"{name}-{uuid.uuid4()}-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.log"
        )
        log_file.parent.mkdir(parents=True, exist_ok=True)
        return open(log_file, "w")

    async def get_tools_for(self, name: str) -> ListToolsResult:
        async with self._client_session(name) as session:
            return await session.list_tools()

    async def get_all_tools(self) -> Dict[str, List[Tool]]:
        out: Dict[str, List[Tool]] = dict()
        for server_name in self.config.get().mcpServers.keys():
            tools = await self.get_tools_for(server_name)
            out[server_name] = tools.tools
        return out

    async def call_tool(self, server_name: str, name: str, **kwargs):
        async with self._client_session(server_name) as session:
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
    mcp_config = McpConfig.for_file_path()
    mcp_client = McpClient(mcp_config)
    for server_name, tools in asyncio.run(mcp_client.get_all_tools()).items():
        for tool in tools:
            register(create_tool_for_mcp(server_name, mcp_client, tool))
