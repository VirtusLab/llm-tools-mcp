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
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TextIO, Any, AsyncContextManager


@dataclass
class _CachedSession:
    session: ClientSession
    connection_cm: AsyncContextManager[Any]
    session_cm: AsyncContextManager[ClientSession]
    log_file: TextIO | None

    async def close(self) -> None:
        await self.session_cm.__aexit__(None, None, None)
        await self.connection_cm.__aexit__(None, None, None)
        if self.log_file:
            self.log_file.close()


class McpClient:
    def __init__(self, config: McpConfig):
        self.config = config
        self._sessions: dict[str, _CachedSession] = {}

    async def __aenter__(self) -> "McpClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    def __del__(self) -> None:
        if self._sessions:
            try:
                asyncio.run(self.close())
            except Exception:
                pass

    async def _get_or_create_session(self, name: str) -> ClientSession | None:
        if name in self._sessions:
            return self._sessions[name].session

        server_config = self.config.get().mcpServers.get(name)
        if not server_config:
            raise ValueError(f"There is no such MCP server: {name}")

        log_file: TextIO | None = None
        connection_cm: AsyncContextManager[Any]

        if isinstance(server_config, SseServerConfig):
            connection_cm = sse_client(server_config.url)
            read, write = await connection_cm.__aenter__()
        elif isinstance(server_config, HttpServerConfig):
            connection_cm = streamablehttp_client(server_config.url)
            read, write, _ = await connection_cm.__aenter__()
        elif isinstance(server_config, StdioServerConfig):
            params = StdioServerParameters(
                command=server_config.command,
                args=server_config.args or [],
                env=server_config.env,
            )
            log_file = self._log_file_for_session(name)
            connection_cm = stdio_client(params, errlog=log_file)
            read, write = await connection_cm.__aenter__()
        else:
            raise ValueError(f"Unknown server config type: {type(server_config)}")

        assert connection_cm is not None
        session_cm = self._client_session_with_logging(name, read, write)
        session = await session_cm.__aenter__()

        if session is None:
            await session_cm.__aexit__(None, None, None)
            await connection_cm.__aexit__(None, None, None)
            if log_file:
                log_file.close()
            return None

        self._sessions[name] = _CachedSession(
            session=session,
            connection_cm=connection_cm,
            session_cm=session_cm,
            log_file=log_file,
        )

        return session

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

    def _log_file_for_session(self, name: str) -> TextIO:
        log_file = (
            self.config.log_path.parent
            / "logs"
            / f"{name}-{uuid.uuid4()}-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.log"
        )
        log_file.parent.mkdir(parents=True, exist_ok=True)
        return open(log_file, "w")

    async def get_tools_for(self, name: str) -> ListToolsResult:
        session = await self._get_or_create_session(name)
        if session is None:
            return ListToolsResult(tools=[])
        return await session.list_tools()

    async def get_all_tools(self) -> dict[str, list[Tool]]:
        tools_for_server: dict[str, list[Tool]] = dict()
        for server_name in self.config.get().mcpServers.keys():
            tools = await self.get_tools_for(server_name)
            tools_for_server[server_name] = tools.tools
        return tools_for_server

    async def call_tool(self, server_name: str, name: str, **kwargs):
        session = await self._get_or_create_session(server_name)
        if session is None:
            return f"Error: Failed to call tool {name} from MCP server {server_name}"
        tool_result = await session.call_tool(name, kwargs)
        return str(tool_result.content)

    async def close(self) -> None:
        """Close all cached MCP sessions."""
        for name, cached in list(self._sessions.items()):
            await cached.close()
            del self._sessions[name]
