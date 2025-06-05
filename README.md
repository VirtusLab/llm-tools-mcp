<div align="center">
   
# `llm-tools-mcp`

![mcp-logo](https://github.com/user-attachments/assets/3e0e9850-6faf-439b-96c2-b672341c1ca5)

**Connect to MCP servers right from your shell. Plugin for [llm](https://github.com/simonw/llm) (by [@simonw](https://github.com/simonw)).**


[![PyPI](https://img.shields.io/pypi/v/llm-tools-mcp.svg)](https://pypi.org/project/llm-tools-mcp/)
[![Changelog](https://img.shields.io/github/v/release/VirtusLab/llm-tools-mcp?include_prereleases&label=changelog)](https://github.com/VirtusLab/llm-tools-mcp/releases)
[![Tests](https://github.com/VirtusLab/llm-tools-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/VirtusLab/llm-tools-mcp/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/VirtusLab/llm-tools-mcp/blob/main/LICENSE)



![demo-long](https://github.com/user-attachments/assets/82ae287f-9e69-4f9c-a26c-49f4f2fd6771)

</div>


> [!Note]
> Current focus: [Authorization #4](https://github.com/VirtusLab/llm-tools-mcp/issues/4)

## New: Client-Daemon Architecture

This plugin now uses a client-daemon architecture for improved performance and reliability:

- **Daemon**: Runs in the background and maintains persistent connections to MCP servers
- **Client**: The LLM plugin communicates with the daemon via gRPC
- **Auto-start**: The daemon is automatically started when needed
- **Process isolation**: MCP server failures don't affect the main LLM process

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/):

```bash
llm install llm-tools-mcp
```

After installation, generate the required gRPC files:

```bash
python setup.py
```

## Usage

> [!WARNING]
> It's recommended to use the `--ta` flag and approve each tool execution.

1. Create `mcp.json` file in `~/.llm-tools-mcp`.

   Example file:

   ```json
   {
     "mcpServers": {
       "filesystem": {
         "command": "npx",
         "args": [
           "-y",
           "@modelcontextprotocol/server-filesystem",
           "~/demo"
         ]
       }
     }
   }
   ```
    
2. List available tools.

   ```sh
   llm tools list
   ```

3. Run `llm` with tools.

   ```sh
   llm --ta -T MCP "what files are in the demo directory? show me contents of one of the files (any)"
   ```

### Daemon Management

The daemon is automatically started when you use MCP tools, but you can also manage it manually:

```bash
# Check daemon status
python mcp_client.py status

# Start the daemon manually
python mcp_client.py start

# Stop the daemon
python mcp_client.py stop

# Check daemon health
python mcp_client.py health
```

### Other examples

**Dynamically change your MCP config:**

```sh
llm --ta -T 'MCP("/path/to/custom/mcp.json")' "your prompt here"
```

## Architecture

```
┌─────────────┐    gRPC     ┌─────────────┐    MCP      ┌─────────────┐
│             │◄─────────►  │             │◄─────────► │             │
│ LLM Client  │             │ MCP Daemon  │             │ MCP Servers │
│             │             │             │             │             │
└─────────────┘             └─────────────┘             └─────────────┘
```

### Components

- **LLM Client** (`llm_tools_mcp.py`): The original LLM plugin, now acts as a gRPC client
- **MCP Daemon** (`mcp_daemon.py`): Background service that maintains connections to MCP servers
- **Client Manager** (`mcp_client.py`): Handles daemon lifecycle and gRPC communication
- **Protocol** (`proto/mcp_daemon.proto`): gRPC service definition

### Benefits

1. **Performance**: Persistent connections to MCP servers reduce startup overhead
2. **Reliability**: Daemon process isolation prevents MCP server issues from affecting LLM
3. **Resource management**: Shared daemon instance across multiple LLM invocations
4. **Monitoring**: Health checks and status monitoring for the daemon
5. **Logging**: Centralized logging for daemon and MCP server interactions

## Development

### Setup

Generate gRPC protobuf files:
```bash
python generate_grpc.py
```

Or run the full setup:
```bash
python setup.py
```

### Current Development Workflow

- Sync dependencies: `uv sync --all-extras`
- Generate gRPC files: `python generate_grpc.py`
- Run linters / type checker: `./check.sh`
- Run tests: `./test.sh`

### Manual Setup

To set up this plugin locally, first checkout the code. Then create a new virtual environment:
```bash
cd llm-tools-mcp
python -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
python -m pip install -e '.[test]'
python generate_grpc.py  # Generate gRPC files
```
To run the tests:
```bash
python -m pytest
```

## Files and Directories

- `~/.llm-tools-mcp/mcp.json` - MCP server configuration
- `~/.llm-tools-mcp/daemon.pid` - Daemon process ID file
- `~/.llm-tools-mcp/logs/` - Daemon and MCP server logs
- `proto/mcp_daemon.proto` - gRPC service definition
- `mcp_daemon_pb2.py` - Generated gRPC Python code (auto-generated)
- `mcp_daemon_pb2_grpc.py` - Generated gRPC Python code (auto-generated)

## To Do

- [x] Release alpha version
- [x] support all transports
  - [x] streamable http
  - [x] sse
  - [x] stdio
- [x] **Implement client-daemon architecture**
  - [x] gRPC protocol definition
  - [x] Daemon server with MCP client logic
  - [x] Client manager with daemon lifecycle
  - [x] Auto-start daemon functionality
  - [x] Replace os.fork with subprocess for portability
- [ ] Build a solid test suite
  - [x] test config file validation
  - [x] test sse with dummy server
  - [x] test stdio with dummy server
  - [x] test http streamable with dummy server ([see #1](https://github.com/Virtuslab/llm-tools-mcp/issues/1))
  - [x] manual test for sse with real server
  - [x] manual test for stdio with real server
  - [x] manual test for http streamable with real server
  - [ ] test client-daemon communication
  - [ ] test daemon lifecycle management
- [x] Redirect `stdout`/`stderr` from the MCP SDK to a file or designated location
- [ ] Reuse stdio connections (handled by daemon)
- [x] **Support non-stdio MCP servers**
- [ ] Handle tool name conflicts (prefix with mcp server name?)
- [ ] Gather feedback on the `~/.llm-tools-mcp` directory naming
- [x] Improve failure handling:
  - [x] When connecting to an MCP server fails
  - [x] When `mcp.json` is malformed
  - [x] When daemon fails to start
  - [x] When gRPC connection fails
- [x] Improve this README:
  - [x] Document client-daemon architecture
  - [x] Add daemon management instructions
  - [x] Add development setup for gRPC
