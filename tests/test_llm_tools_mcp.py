import tempfile
import json
import os
import asyncio
from pathlib import Path

from llm_tools_mcp import McpConfig, McpClient


def test_integration():
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file1 = Path(temp_dir) / "test1.txt"
        test_file2 = Path(temp_dir) / "test2.txt"

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
                            temp_dir,
                        ],
                    }
                }
            }

            json.dump(mcp_config, config_file, indent=2)
            config_file_path = config_file.name

        try:
            mcp_config_obj = McpConfig(path=config_file_path)
            mcp_client = McpClient(mcp_config_obj)

            all_tools = asyncio.run(mcp_client.get_all_tools())

            print(f"Found {len(all_tools)} server(s):")
            for server_name, tools in all_tools.items():
                print(f"  Server '{server_name}' has {len(tools)} tools:")
                for tool in tools:
                    print(f"    - {tool.name}: {tool.description}")

            assert len(all_tools) > 0, "Should have at least one server"
            assert "filesystem" in all_tools, "Should have filesystem server"
            assert len(all_tools["filesystem"]) > 0, (
                "Filesystem server should have tools"
            )

            filesystem_tools = all_tools["filesystem"]
            tool_names = [tool.name for tool in filesystem_tools]

            expected_tools = ["read_file", "write_file", "list_directory"]
            found_expected = [tool for tool in expected_tools if tool in tool_names]

            print(f"Found expected tools: {found_expected}")
            assert len(found_expected) > 0, (
                f"Should find at least one expected tool from {expected_tools}"
            )

        finally:
            os.unlink(config_file_path)


if __name__ == "__main__":
    print("Running MCP integration test...")
    test_integration()
    print("Integration test passed!")
