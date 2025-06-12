from typing import Annotated
from pydantic import BaseModel, Discriminator, Field, Tag
from llm_tools_mcp.defaults import DEFAULT_CONFIG_DIR
from llm_tools_mcp.defaults import DEFAULT_MCP_JSON_PATH


import json
from pathlib import Path


def _get_discriminator_value(v: dict) -> str:
    if "type" in v:
        type_value = v["type"]
        if isinstance(type_value, str):
            allowed_types = ["stdio", "sse", "http"]
            if type_value in allowed_types:
                return type_value
            else:
                raise ValueError(
                    f"Unknown server 'type'. Provided 'type': {type_value}. Allowed types: {allowed_types}"
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
        elif "url" in v:
            # inference rules kinda like in FastMCP 2.x
            # https://gofastmcp.com/clients/transports#overview
            if "/sse" in v["url"]:
                return "sse"
            else:
                return "http"
        elif "command" in v:
            return "stdio"
        else:
            raise ValueError(
                "Could not deduce MCP server type. Provide 'url' or 'command'. You can explicitly specify the type with 'type' field."
            )


class StdioServerConfig(BaseModel):
    command: str = Field()
    args: list[str] | None = Field(default=None)
    env: dict[str, str] | None = Field(default=None)


class SseServerConfig(BaseModel):
    url: str = Field()


class HttpServerConfig(BaseModel):
    url: str = Field()


StdioOrSseServerConfig = Annotated[
    Annotated[StdioServerConfig, Tag("stdio")]
    | Annotated[HttpServerConfig, Tag("http")]
    | Annotated[SseServerConfig, Tag("sse")],
    Discriminator(_get_discriminator_value),
]


class McpConfigType(BaseModel):
    mcpServers: dict[str, StdioOrSseServerConfig]


class McpConfig:
    def __init__(
        self,
        config: McpConfigType,
        log_path: Path = Path(DEFAULT_CONFIG_DIR) / Path("logs"),
    ):
        self.config = config
        self.log_path = log_path.expanduser()

    @classmethod
    def for_file_path(cls, path: str = DEFAULT_MCP_JSON_PATH):
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
