from contextlib import asynccontextmanager
import asyncio
from typing import Dict, List, TypedDict
from mcp import Tool
import pytest
import uvicorn
from starlette.applications import Starlette

from llm_tools_mcp import McpConfig

from mcp.server.fastmcp import FastMCP


class JsonValidationTestCase(TypedDict):
    input_json: str
    expected_error_contains: List[str]


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


json_validation_test_data: List[JsonValidationTestCase] = [
    {
        "input_json": """
        {
            "invalid": "asd"
        }
        """,
        "expected_error_contains": ["mcpServers", "Field required"],
    },
    {
        "input_json": """
        []
        """,
        "expected_error_contains": ["Input should be an object"],
    },
    {
        "input_json": """
        {
            "mcpServers": []
        }
        """,
        "expected_error_contains": [
            "mcpServers",
            "Input should be an object",
        ],
    },
    {
        "input_json": """
        {
            "mcpServers": {
                "name": {
                    "unknown": "a"
                }
            }
        }
        """,
        "expected_error_contains": ["Could not deduce MCP server type"],
    },
    {
        "input_json": """
        {
            "mcpServers": {
                "name": {
                    "command": "whatever",
                    "url": "https://url"
                }
            }
        }
        """,
        "expected_error_contains": [
            "Only 'url' or 'command' is allowed",
            "whatever",
            "https://url",
        ],
    },
    {
        "input_json": """
        {
            "mcpServers": {
                "name": {
                    "command": "whatever",
                    "type": "sse"
                }
            }
        }
        """,
        "expected_error_contains": ["Field required"],
    },
    {
        "input_json": """
        {
            "mcpServers": {
                "name": {
                    "command": "whatever",
                    "type": "invalid"
                }
            }
        }
        """,
        "expected_error_contains": ["Unknown server 'type'", "invalid"],
    },
    {
        "input_json": """
        {
            "mcpServers": {
                "name": {
                    "command": "whatever",
                    "url": "https://url"
                }
            }
        }
        """,
        "expected_error_contains": [
            "Only 'url' or 'command' is allowed",
            "whatever",
            "https://url",
        ],
    },
]


def tool_names(all_tools: Dict[str, List[Tool]]) -> List[str]:
    return [tool.name for tools in all_tools.values() for tool in tools]


@pytest.mark.parametrize("test_case", json_validation_test_data)
def test_mcp_json_validation(test_case):
    with pytest.raises(ValueError) as excinfo:
        McpConfig.for_json_content(test_case["input_json"])
    for expected_error in test_case["expected_error_contains"]:
        assert expected_error in str(excinfo.value)
