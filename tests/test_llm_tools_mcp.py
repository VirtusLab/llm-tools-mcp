import socket
import tempfile
import json
import asyncio
from pathlib import Path
import pytest

from llm_tools_mcp import McpConfig, McpClient

from mcp.server.fastmcp import FastMCP, Context


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.mark.asyncio
async def test_sse():
    port = get_free_port()
    print(f"Using port {port}")
    mcp = FastMCP("My App SSE", port=port)

    @mcp.tool()
    async def long_task(files: list[str], ctx: Context) -> str:
        """Process multiple files with progress tracking"""
        for i, file in enumerate(files):
            await ctx.info(f"Processing {file}")
            await ctx.report_progress(i, len(files))
        return "Processing complete: [1,23]"

    # Start the MCP server as a background task
    server_task = asyncio.create_task(mcp.run_sse_async())

    # Give the server time to start
    await asyncio.sleep(2)

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as config_file:
            mcp_config = {
                "mcpServers": {
                    "test_sse_server": {"url": f"http://localhost:{port}/sse"}
                }
            }

            json.dump(mcp_config, config_file, indent=2)
            config_file_path = config_file.name

        mcp_config_obj = McpConfig(path=config_file_path)
        mcp_client = McpClient(mcp_config_obj)

        all_tools = await mcp_client.get_all_tools()

        print(f"Found {len(all_tools)} server(s):")
        for server_name, tools in all_tools.items():
            print(f"  Server '{server_name}' has {len(tools)} tools:")
            for tool in tools:
                print(f"    - {tool.name}: {tool.description}")

        assert len(all_tools) > 0, "Should have at least one server"
        assert "test_sse_server" in all_tools, "Should have test_sse_server"
        assert "long_task" in map(lambda x: x.name, all_tools["test_sse_server"]), (
            "Server should have long_task tool"
        )

        result = await mcp_client.call_tool(
            "test_sse_server", "long_task", files=["file1.txt", "file2.txt"]
        )

        assert result is not None, "Tool call should return a result"
        result_str = str(result)
        assert "Processing complete" in result_str, "Should find completion message"
        print("SSE tool call test passed!")

    finally:
        # Cancel the server task
        print("cancelling server task")
        server_task.cancel()
        try:
            print("awaiting server task")
            await server_task
        except asyncio.CancelledError:
            print("server task cancelled")
            pass


@pytest.mark.asyncio
async def test_stdio():
    # Use a fixed test directory instead of tempfile.TemporaryDirectory
    # to avoid issues with the filesystem MCP server
    test_dir = Path.cwd() / "test_mcp_temp"
    test_dir.mkdir(exist_ok=True)

    try:
        test_file1 = test_dir / "test1.txt"
        test_file2 = test_dir / "test2.txt"

        test_file1.write_text("This is test file 1")
        test_file2.write_text("This is test file 2")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as config_file:
            mcp_config = {
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

            json.dump(mcp_config, config_file, indent=2)
            config_file_path = config_file.name

        mcp_config_obj = McpConfig(path=config_file_path)
        mcp_client = McpClient(mcp_config_obj)

        all_tools = await mcp_client.get_all_tools()

        print(f"Found {len(all_tools)} server(s):")
        for server_name, tools in all_tools.items():
            print(f"  Server '{server_name}' has {len(tools)} tools:")
            for tool in tools:
                print(f"    - {tool.name}: {tool.description}")

        assert len(all_tools) > 0, "Should have at least one server"
        assert "filesystem" in all_tools, "Should have filesystem server"
        assert len(all_tools["filesystem"]) > 0, "Filesystem server should have tools"

        filesystem_tools = all_tools["filesystem"]
        tool_names = [tool.name for tool in filesystem_tools]

        expected_tools = ["read_file", "write_file", "list_directory"]
        found_expected = [tool for tool in expected_tools if tool in tool_names]

        print(f"Found expected tools: {found_expected}")
        assert len(found_expected) > 0, (
            f"Should find at least one expected tool from {expected_tools}"
        )
        assert "read_file" in map(lambda x: x.name, filesystem_tools), (
            "Should have read_file tool"
        )

        # Test calling a tool
        print("\nTesting read_file tool...")
        result = await mcp_client.call_tool(
            "filesystem", "read_file", path=str(test_file1)
        )
        print(f"File read result: {result}")

        # Verify the result contains our test file content
        assert result is not None, "Tool call should return a result"
        result_str = str(result)
        assert "This is test file 1" in result_str, "Should find test file content"
        print("Tool call test passed!")

    finally:
        # Clean up test directory
        import shutil

        if test_dir.exists():
            shutil.rmtree(test_dir)


# TODO: Does not work due to:
# ERROR:    ASGI callable returned without completing response.
@pytest.mark.asyncio
@pytest.mark.skip(reason="https://github.com/VirtusLab/llm-tools-mcp/issues/1")
async def test_http():
    # random available port

    port = get_free_port()
    mcp_http = FastMCP("My App Http", port=port, debug=True)

    @mcp_http.tool()
    async def long_task_http(files: list[str], ctx: Context) -> str:
        """Process multiple files with progress tracking"""
        return "Processing complete: [1,23]"

    # Start the MCP server as a background task
    server_task = asyncio.create_task(mcp_http.run_streamable_http_async())

    # Give the server time to start
    await asyncio.sleep(2)

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as config_file:
            mcp_config = {
                "mcpServers": {
                    "test_http_server": {
                        "type": "http",
                        "url": f"http://localhost:{port}/mcp",
                    }
                }
            }

            json.dump(mcp_config, config_file, indent=2)
            config_file_path = config_file.name

        mcp_config_obj = McpConfig(path=config_file_path)
        mcp_client = McpClient(mcp_config_obj)

        print("About to get all tools")
        all_tools = await mcp_client.get_all_tools()

        print(f"Found {len(all_tools)} server(s):")
        for server_name, tools in all_tools.items():
            print(f"  Server '{server_name}' has {len(tools)} tools:")
            for tool in tools:
                print(f"    - {tool.name}: {tool.description}")

        assert len(all_tools) > 0, "Should have at least one server"
        assert "test_http_server" in all_tools, "Should have test_http_server"
        assert "long_task_http" in map(
            lambda x: x.name, all_tools["test_http_server"]
        ), "Server should have long_task tool"

        result = await mcp_client.call_tool(
            "test_http_server", "long_task_http", files=["file1.txt", "file2.txt"]
        )

        assert result is not None, "Tool call should return a result"
        result_str = str(result)
        assert "Processing complete" in result_str, "Should find completion message"
        print("HTTP tool call test passed!")

    finally:
        # Cancel the server task
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
