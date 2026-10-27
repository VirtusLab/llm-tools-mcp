import asyncio
import json
import sys
import textwrap
from contextlib import nullcontext
from unittest.mock import AsyncMock

import pytest
from mcp.shared.exceptions import McpError

from llm_tools_mcp.mcp_client import McpClient
from llm_tools_mcp.mcp_config import McpConfig
from llm_tools_mcp.register_tools import _get_tools_for_llm


@pytest.fixture
def client(tmp_path):
    return McpClient(
        McpConfig.for_json_content('{"mcpServers": {}}').with_log_path(
            tmp_path / "mcp.log"
        )
    )


@pytest.fixture
def session(monkeypatch):
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = False
    monkeypatch.setattr("llm_tools_mcp.mcp_client.ClientSession", lambda *args: session)
    return session


@pytest.mark.parametrize("error_type", [ValueError, asyncio.CancelledError])
async def test_session_body_error_propagates(client, session, capsys, error_type):
    error = error_type("body failed")
    with pytest.raises(error_type) as raised:
        async with client._client_session_with_logging("local", None, None) as result:
            assert result is session
            raise error

    assert raised.value is error
    assert capsys.readouterr().err == ""
    session.__aexit__.assert_awaited_once()


@pytest.mark.parametrize("full_errors", [False, True])
@pytest.mark.parametrize("body_error", [False, True])
async def test_initialization_error_fallback(
    client, session, capsys, monkeypatch, full_errors, body_error
):
    session.initialize.side_effect = ValueError("initialization failed")
    if full_errors:
        monkeypatch.setenv("LLM_TOOLS_MCP_FULL_ERRORS", "1")
    else:
        monkeypatch.delenv("LLM_TOOLS_MCP_FULL_ERRORS", raising=False)

    with (
        pytest.raises(ValueError, match="body failed") if body_error else nullcontext()
    ):
        async with client._client_session_with_logging("local", None, None) as result:
            assert result is None
            if body_error:
                raise ValueError("body failed")

    warning = capsys.readouterr().err
    assert (
        "Failed to connect to the 'local' MCP server: initialization failed" in warning
    )
    assert str(client.config.log_path) in warning
    assert ("Traceback" in warning) is full_errors
    session.__aexit__.assert_awaited_once()


@pytest.fixture
def protocol_client(tmp_path):
    server = tmp_path / "server.py"
    server.write_text(
        textwrap.dedent("""\
            import asyncio
            import sys
            from mcp import types
            from mcp.server import Server
            from mcp.server.stdio import stdio_server
            from mcp.shared.exceptions import McpError

            mode = sys.argv[1]
            app = Server("protocol-test")

            @app.list_tools()
            async def tools():
                if mode == "list":
                    raise McpError(types.ErrorData(code=-32603, message="Discovery unavailable"))
                return [types.Tool(name="example", inputSchema={"type": "object"})]

            async def call(request):
                if mode == "call":
                    raise McpError(types.ErrorData(code=-32603, message="Backend unavailable"))
                return types.ServerResult(types.CallToolResult(
                    content=[types.TextContent(type="text", text="success")]
                ))

            app.request_handlers[types.CallToolRequest] = call

            async def main():
                async with stdio_server() as (read, write):
                    await app.run(read, write, app.create_initialization_options())

            asyncio.run(main())
        """)
    )

    def create(mode):
        config = McpConfig.for_json_content(
            json.dumps(
                {
                    "mcpServers": {
                        "local": {
                            "command": sys.executable,
                            "args": [str(server), mode],
                        }
                    }
                }
            )
        ).with_log_path(tmp_path / "mcp.log")
        return McpClient(config)

    return create


def leaf_exceptions(error):
    children = getattr(error, "exceptions", ())
    if not children:
        return [error]
    return [leaf for child in children for leaf in leaf_exceptions(child)]


@pytest.mark.parametrize("operation", ["list", "call"])
def test_stdio_protocol_error_propagates(protocol_client, capsys, operation):
    with pytest.raises(BaseException) as raised:
        tools = _get_tools_for_llm(protocol_client(operation))
        tools[0].implementation()

    errors = leaf_exceptions(raised.value)
    assert len(errors) == 1
    assert isinstance(errors[0], McpError)
    assert str(errors[0]) == (
        "Discovery unavailable" if operation == "list" else "Backend unavailable"
    )
    assert "Failed to connect" not in capsys.readouterr().err


def test_stdio_success(protocol_client):
    tools = _get_tools_for_llm(protocol_client("success"))
    assert len(tools) == 1
    assert "success" in tools[0].implementation()
