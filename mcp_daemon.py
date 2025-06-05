#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import signal
import sys
import traceback
from concurrent import futures
from pathlib import Path
from typing import Dict, List

import grpc
from grpc_reflection.v1alpha import reflection

# Import the original MCP client code
from llm_tools_mcp import McpClient, McpConfig

# Import generated gRPC code (will be generated)
try:
    import mcp_daemon_pb2
    import mcp_daemon_pb2_grpc
except ImportError:
    print("gRPC protobuf files not found. Please run: python -m grpc_tools.protoc --python_out=. --grpc_python_out=. --proto_path=proto proto/mcp_daemon.proto")
    sys.exit(1)

DEFAULT_PORT = 50051
DEFAULT_PIDFILE = os.path.expanduser("~/.llm-tools-mcp/daemon.pid")
VERSION = "0.3.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class McpDaemonServicer(mcp_daemon_pb2_grpc.McpDaemonServicer):
    def __init__(self):
        self._mcp_clients: Dict[str, McpClient] = {}
        self._configs: Dict[str, McpConfig] = {}

    def _get_mcp_client(self, config_path: str) -> McpClient:
        """Get or create an MCP client for the given config path."""
        if config_path not in self._mcp_clients:
            config = McpConfig.for_file_path(config_path)
            self._mcp_clients[config_path] = McpClient(config)
            self._configs[config_path] = config
        return self._mcp_clients[config_path]

    async def GetAllTools(self, request, context):
        """Get all tools from all MCP servers."""
        try:
            mcp_client = self._get_mcp_client(request.config_path)
            tools_dict = await mcp_client.get_all_tools()
            
            response = mcp_daemon_pb2.GetAllToolsResponse()
            
            for server_name, tools in tools_dict.items():
                tool_list = mcp_daemon_pb2.ToolList()
                for tool in tools:
                    proto_tool = mcp_daemon_pb2.Tool(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=json.dumps(tool.inputSchema) if tool.inputSchema else "{}"
                    )
                    tool_list.tools.append(proto_tool)
                response.tools_by_server[server_name].CopyFrom(tool_list)
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting all tools: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error getting tools: {str(e)}")
            return mcp_daemon_pb2.GetAllToolsResponse()

    async def CallTool(self, request, context):
        """Call a specific tool on a specific MCP server."""
        try:
            mcp_client = self._get_mcp_client(request.config_path)
            
            # Parse arguments from JSON string
            arguments = json.loads(request.arguments) if request.arguments else {}
            
            result = await mcp_client.call_tool(
                request.server_name,
                request.tool_name,
                **arguments
            )
            
            return mcp_daemon_pb2.CallToolResponse(
                result=str(result),
                success=True,
                error=""
            )
            
        except Exception as e:
            logger.error(f"Error calling tool {request.tool_name}: {e}")
            return mcp_daemon_pb2.CallToolResponse(
                result="",
                success=False,
                error=str(e)
            )

    async def Health(self, request, context):
        """Health check endpoint."""
        return mcp_daemon_pb2.HealthResponse(
            healthy=True,
            version=VERSION
        )


class McpDaemonServer:
    def __init__(self, port: int = DEFAULT_PORT):
        self.port = port
        self.server = None
        self.servicer = McpDaemonServicer()

    async def start(self):
        """Start the gRPC server."""
        self.server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        
        mcp_daemon_pb2_grpc.add_McpDaemonServicer_to_server(
            self.servicer, self.server
        )
        
        # Enable reflection for debugging
        SERVICE_NAMES = (
            mcp_daemon_pb2.DESCRIPTOR.services_by_name['McpDaemon'].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(SERVICE_NAMES, self.server)
        
        listen_addr = f'[::]:{self.port}'
        self.server.add_insecure_port(listen_addr)
        
        logger.info(f"Starting MCP daemon server on {listen_addr}")
        await self.server.start()
        
        # Write PID file
        self._write_pidfile()
        
        return self.server

    async def stop(self):
        """Stop the gRPC server."""
        if self.server:
            logger.info("Stopping MCP daemon server")
            await self.server.stop(grace=5)
            self._remove_pidfile()

    def _write_pidfile(self):
        """Write the current process PID to a file."""
        pidfile_path = Path(DEFAULT_PIDFILE)
        pidfile_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pidfile_path, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"PID file written to {pidfile_path}")

    def _remove_pidfile(self):
        """Remove the PID file."""
        pidfile_path = Path(DEFAULT_PIDFILE)
        if pidfile_path.exists():
            pidfile_path.unlink()
            logger.info(f"PID file removed: {pidfile_path}")


async def main():
    """Main function to run the daemon server."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MCP Daemon Server')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                       help=f'Port to listen on (default: {DEFAULT_PORT})')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon (fork to background)')
    args = parser.parse_args()

    if args.daemon:
        # Fork to background
        pid = os.fork()
        if pid > 0:
            # Parent process exits
            print(f"Daemon started with PID {pid}")
            sys.exit(0)
        
        # Child process continues
        os.setsid()
        os.chdir('/')
        
        # Redirect stdout/stderr to log file
        log_dir = Path(DEFAULT_PIDFILE).parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "daemon.log"
        
        with open(log_file, 'a') as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
            os.dup2(f.fileno(), sys.stderr.fileno())

    server = McpDaemonServer(port=args.port)
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(server.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await server.start()
        await server.server.wait_for_termination()
    except Exception as e:
        logger.error(f"Server error: {e}")
        traceback.print_exc()
    finally:
        await server.stop()


if __name__ == '__main__':
    asyncio.run(main())