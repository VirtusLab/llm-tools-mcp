from contextlib import asynccontextmanager
import socket
import json
import asyncio
from pathlib import Path
from typing import Dict, List
from mcp import Tool
import pytest
import uvicorn
from starlette.applications import Starlette

from llm_tools_mcp import McpConfig, McpClient

from mcp.server.fastmcp import FastMCP, Context


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@asynccontextmanager
async def server_context(mcp: FastMCP, starlette_app: Starlette):
    config = uvicorn.Config(
        starlette_app,
        host=mcp.settings.host,
        port=mcp.settings.port,
        log_level=mcp.settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(2)

    try:
        yield
    finally:
        await server.shutdown()
        server_task.cancel()


def tool_names(all_tools: Dict[str, List[Tool]]) -> List[str]:
    return [tool.name for tools in all_tools.values() for tool in tools]


@pytest.mark.asyncio
async def test_sse():
    port = get_free_port()
    print(f"Using port {port}")
    mcp = FastMCP(
        "My App SSE",
        port=port,
    )

    @mcp.tool()
    async def long_task(files: list[str], ctx: Context) -> str:
        """Process multiple files with progress tracking"""
        for i, file in enumerate(files):
            await ctx.info(f"Processing {file}")
            await ctx.report_progress(i, len(files))
        return "Tool output"

    async with server_context(mcp, mcp.sse_app()):
        mcp_config_content = json.dumps(
            {"mcpServers": {"test_sse_server": {"url": f"http://localhost:{port}/sse"}}}
        )

        mcp_config_obj = McpConfig.for_json_content(mcp_config_content)
        mcp_client = McpClient(mcp_config_obj)

        server_to_tools = await mcp_client.get_all_tools()

        assert "test_sse_server" in server_to_tools
        assert "long_task" in tool_names(server_to_tools)

        result = await mcp_client.call_tool(
            "test_sse_server", "long_task", files=["file1.txt", "file2.txt"]
        )

        assert result is not None, "Tool call should return a result"
        result_str = str(result)
        assert "Tool output" in result_str, "Should find completion message"


@pytest.mark.asyncio
async def test_stdio():
    test_dir = Path.cwd() / "test_mcp_temp"
    test_dir.mkdir(exist_ok=True)

    try:
        test_file1 = test_dir / "test1.txt"
        test_file2 = test_dir / "test2.txt"

        test_file1.write_text("This is test file 1")
        test_file2.write_text("This is test file 2")

        mcp_config_content = json.dumps(
            {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": [
                            "-y",
                            "@modelcontextprotocol/server-filesystem",
                            str(test_dir),
                        ],
                    }
                }
            }
        )

        mcp_config_obj = McpConfig.for_json_content(mcp_config_content)
        mcp_client = McpClient(mcp_config_obj)

        server_to_tools = await mcp_client.get_all_tools()

        assert "filesystem" in server_to_tools, "Should have filesystem server"

        assert "read_file" in tool_names(server_to_tools)
        assert "write_file" in tool_names(server_to_tools)
        assert "list_directory" in tool_names(server_to_tools)

        result = await mcp_client.call_tool(
            "filesystem", "read_file", path=str(test_file1)
        )

        assert result is not None, "Tool call should return a result"
        result_str = str(result)
        assert "This is test file 1" in result_str, "Should find test file content"

    finally:
        import shutil

        if test_dir.exists():
            shutil.rmtree(test_dir)


@pytest.mark.asyncio
async def test_http():
    port = get_free_port()
    mcp_http = FastMCP("My App Http", port=port, debug=True)

    @mcp_http.tool()
    async def long_task_http(files: list[str]) -> str:
        """Process multiple files with progress tracking"""
        return "Tool output"

    async with server_context(mcp_http, mcp_http.streamable_http_app()):
        mcp_config_content = json.dumps(
            {
                "mcpServers": {
                    "test_http_server": {
                        "type": "http",
                        "url": f"http://localhost:{port}/mcp",
                    }
                }
            }
        )

        mcp_config_obj = McpConfig.for_json_content(mcp_config_content)
        mcp_client = McpClient(mcp_config_obj)

        server_to_tools = await mcp_client.get_all_tools()

        assert "test_http_server" in server_to_tools, "Should have test_http_server"
        assert "long_task_http" in tool_names(server_to_tools)

        result = await mcp_client.call_tool(
            "test_http_server", "long_task_http", files=["file1.txt", "file2.txt"]
        )

        assert result is not None, "Tool call should return a result"
        result_str = str(result)
        assert "Tool output" in result_str, "Should find completion message"
