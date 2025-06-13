from llm_tools_mcp.mcp_config import McpConfig, SseServerConfig, StdioServerConfig
from llm_tools_mcp.mcp_config import HttpServerConfig
import sys

from mcp import (
    ClientSession,
    ListToolsResult,
    StdioServerParameters,
    Tool,
    stdio_client,
)
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client


import datetime
import os
import traceback
import uuid
from contextlib import asynccontextmanager
from typing import TextIO


@asynccontextmanager
async def enrich_exceptions(**details):
    try:
        yield
    except Exception as e:
        raise Exception(
            f"There was an error while handling (llm-tools-mcp plugin). Details: {details}"
        ) from e


class McpClient:
    def __init__(self, config: McpConfig):
        self.config = config

    @asynccontextmanager
    async def _client_session_with_logging(self, name, read, write):
        async with ClientSession(read, write) as session:
            try:
                await session.initialize()
                yield session
            except Exception as e:
                print(
                    f"Warning: Failed to connect to the '{name}' MCP server: {e}",
                    file=sys.stderr,
                )
                print(
                    f"Tools from '{name}' will be unavailable (run with LLM_TOOLS_MCP_FULL_ERRORS=1) or see logs: {self.config.log_path}",
                    file=sys.stderr,
                )
                if os.environ.get("LLM_TOOLS_MCP_FULL_ERRORS", None):
                    print(traceback.format_exc(), file=sys.stderr)
                yield None

    @asynccontextmanager
    async def _client_session(self, name: str):
        server_config = self.config.get().mcpServers.get(name)
        if not server_config:
            raise ValueError(f"There is no such MCP server: {name}")
        if isinstance(server_config, SseServerConfig):
            async with sse_client(server_config.url) as (read, write):
                async with self._client_session_with_logging(
                    name, read, write
                ) as session:
                    yield session
        elif isinstance(server_config, HttpServerConfig):
            async with streamablehttp_client(server_config.url) as (read, write, _):
                async with self._client_session_with_logging(
                    name, read, write
                ) as session:
                    yield session
        elif isinstance(server_config, StdioServerConfig):
            params = StdioServerParameters(
                command=server_config.command,
                args=server_config.args or [],
                env=server_config.env,
            )
            log_file = self._log_file_for_session(name)
            async with stdio_client(params, errlog=log_file) as (read, write):
                async with self._client_session_with_logging(
                    name, read, write
                ) as session:
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
        async with enrich_exceptions(server_name=name):
            async with self._client_session(name) as session:
                if session is None:
                    return ListToolsResult(tools=[])
                return await session.list_tools()

    async def get_all_tools(self) -> dict[str, list[Tool]]:
        tools_for_server: dict[str, list[Tool]] = dict()
        for server_name in self.config.get().mcpServers.keys():
            async with enrich_exceptions(server_name=server_name):
                tools = await self.get_tools_for(server_name)
                tools_for_server[server_name] = tools.tools
        return tools_for_server

    async def call_tool(self, server_name: str, name: str, **kwargs):
        async with enrich_exceptions(server_name=server_name, tool_name=name):
            async with self._client_session(server_name) as session:
                if session is None:
                    return (
                    f"Error: Failed to call tool {name} from MCP server {server_name}"
                )
            tool_result = await session.call_tool(name, kwargs)
            return str(tool_result.content)
