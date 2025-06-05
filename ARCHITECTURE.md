# Client-Daemon Architecture Implementation

This document describes the implementation of the client-daemon architecture for llm-tools-mcp.

## Overview

The llm-tools-mcp plugin has been refactored from a direct MCP client architecture to a client-daemon architecture using gRPC for communication. This change improves performance, reliability, and resource management.

## Components

### 1. Protocol Definition (`proto/mcp_daemon.proto`)

Defines the gRPC service interface between client and daemon:

- `GetAllTools`: Retrieve all available tools from all MCP servers
- `CallTool`: Execute a specific tool on a specific MCP server  
- `Health`: Check daemon health status

**Message Types:**
- Tool metadata (name, description, input schema)
- Server-tool mappings
- Tool call requests/responses
- Health check messages

### 2. MCP Daemon (`mcp_daemon.py`)

Background service that:

- Maintains persistent connections to MCP servers
- Implements the gRPC service interface
- Manages MCP client instances per config file
- Handles tool execution requests
- Provides health monitoring
- Logs to dedicated files

**Key Features:**
- Async gRPC server using grpcio
- Per-config MCP client caching
- Graceful shutdown handling
- PID file management
- Configurable logging

### 3. Client Manager (`mcp_client.py`)

Handles daemon lifecycle and gRPC communication:

- **DaemonManager**: Start/stop/status daemon process
- **McpDaemonClient**: gRPC client for daemon communication
- **McpClientManager**: High-level interface with auto-daemon-start

**Key Features:**
- Automatic daemon startup on first use
- Process existence checking via PID files
- Graceful daemon shutdown with SIGTERM/SIGKILL
- Health checks and connection retry logic
- CLI interface for manual daemon management

### 4. LLM Plugin (`llm_tools_mcp.py`)

Updated to use the daemon instead of direct MCP connections:

- Creates `McpClientManager` instances
- Converts daemon responses to LLM tool format
- Maintains backward compatibility with existing configuration
- Automatic cleanup of daemon connections

## Process Flow

```
1. LLM invokes tool → llm_tools_mcp.py
2. Check if daemon running → DaemonManager.is_daemon_running()
3. Start daemon if needed → DaemonManager.start_daemon()
4. Connect to daemon → McpDaemonClient.connect()
5. Request tools → GetAllTools gRPC call
6. Execute tool → CallTool gRPC call
7. Return result → Tool implementation
```

## Benefits

### Performance
- **Persistent connections**: MCP servers stay connected between LLM invocations
- **Reduced startup time**: No need to reconnect to MCP servers on each use
- **Shared resources**: Single daemon serves multiple LLM processes

### Reliability
- **Process isolation**: MCP server crashes don't affect LLM process
- **Graceful error handling**: Daemon failures are isolated and recoverable
- **Connection retry**: Automatic reconnection to failed MCP servers

### Resource Management
- **Memory efficiency**: Shared daemon instance across invocations
- **Connection pooling**: Reuse of MCP connections
- **Centralized logging**: All MCP interactions logged in one place

### Maintainability
- **Clear separation**: Client logic separated from MCP server communication
- **Testability**: Each component can be tested independently
- **Extensibility**: Easy to add new gRPC endpoints

## Configuration

### File Locations
- `~/.llm-tools-mcp/mcp.json` - MCP server configuration (unchanged)
- `~/.llm-tools-mcp/daemon.pid` - Daemon process ID
- `~/.llm-tools-mcp/logs/daemon.log` - Daemon logs
- `~/.llm-tools-mcp/logs/*.log` - MCP server logs

### Daemon Options
```bash
python mcp_daemon.py --port 50051 --log-file /path/to/log --log-level INFO
```

### Client CLI
```bash
python mcp_client.py start|stop|status|health
```

## Migration from Direct Client

The migration is transparent for end users:

1. **Same configuration**: `mcp.json` format unchanged
2. **Same LLM interface**: Tool usage identical
3. **Automatic daemon**: No manual daemon management required
4. **Backward compatibility**: All existing features preserved

## Development Setup

1. **Install dependencies**: 
   ```bash
   pip install grpcio grpcio-tools grpcio-reflection
   ```

2. **Generate gRPC files**:
   ```bash
   python generate_grpc.py
   # or
   make grpc
   ```

3. **Development workflow**:
   ```bash
   make setup    # Generate gRPC files
   make test     # Run tests
   make lint     # Run linters
   make clean    # Clean generated files
   ```

## Testing the Architecture

### Manual Testing

1. **Generate gRPC files**:
   ```bash
   python generate_grpc.py
   ```

2. **Start daemon manually**:
   ```bash
   python mcp_client.py start
   ```

3. **Check daemon status**:
   ```bash
   python mcp_client.py health
   ```

4. **Use with LLM** (requires MCP server configuration):
   ```bash
   llm --ta -T MCP "test prompt"
   ```

5. **Stop daemon**:
   ```bash
   python mcp_client.py stop
   ```

### Error Scenarios

The implementation handles various error scenarios:

- **Daemon not running**: Auto-starts on first tool use
- **Daemon startup failure**: Graceful fallback with error messages
- **MCP server unavailable**: Individual server failures don't affect others
- **gRPC connection failure**: Automatic reconnection attempts
- **Configuration errors**: Detailed error messages for debugging

## Future Enhancements

Potential improvements to the architecture:

1. **Connection pooling**: Multiple daemon instances for load balancing
2. **Hot configuration reload**: Update MCP servers without daemon restart
3. **Metrics collection**: Performance and usage monitoring
4. **Security**: Authentication and authorization for gRPC
5. **Clustering**: Multiple daemon instances for high availability