#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import grpc

# Import generated gRPC code (will be generated)
try:
    import mcp_daemon_pb2
    import mcp_daemon_pb2_grpc
except ImportError:
    print("gRPC protobuf files not found. Please run: python -m grpc_tools.protoc --python_out=. --grpc_python_out=. --proto_path=proto proto/mcp_daemon.proto")
    sys.exit(1)

DEFAULT_PORT = 50051
DEFAULT_PIDFILE = os.path.expanduser("~/.llm-tools-mcp/daemon.pid")
DAEMON_STARTUP_TIMEOUT = 10  # seconds

# Configure logging
logger = logging.getLogger(__name__)


class McpDaemonClient:
    """Client for communicating with the MCP daemon via gRPC."""
    
    def __init__(self, host: str = 'localhost', port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.channel = None
        self.stub = None

    async def connect(self) -> bool:
        """Connect to the daemon. Returns True if successful, False otherwise."""
        try:
            self.channel = grpc.aio.insecure_channel(f'{self.host}:{self.port}')
            self.stub = mcp_daemon_pb2_grpc.McpDaemonStub(self.channel)
            
            # Test connection with health check
            await self.health_check()
            return True
            
        except Exception as e:
            logger.debug(f"Failed to connect to daemon: {e}")
            if self.channel:
                await self.channel.close()
                self.channel = None
                self.stub = None
            return False

    async def disconnect(self):
        """Disconnect from the daemon."""
        if self.channel:
            await self.channel.close()
            self.channel = None
            self.stub = None

    async def health_check(self) -> bool:
        """Check if the daemon is healthy."""
        if not self.stub:
            return False
            
        try:
            request = mcp_daemon_pb2.HealthRequest()
            response = await self.stub.Health(request, timeout=5)
            return response.healthy
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    async def get_all_tools(self, config_path: str) -> Dict[str, List[dict]]:
        """Get all tools from all MCP servers."""
        if not self.stub:
            raise RuntimeError("Not connected to daemon")
            
        request = mcp_daemon_pb2.GetAllToolsRequest(config_path=config_path)
        response = await self.stub.GetAllTools(request)
        
        tools_dict = {}
        for server_name, tool_list in response.tools_by_server.items():
            tools = []
            for tool in tool_list.tools:
                tools.append({
                    'name': tool.name,
                    'description': tool.description,
                    'input_schema': json.loads(tool.input_schema) if tool.input_schema else {}
                })
            tools_dict[server_name] = tools
            
        return tools_dict

    async def call_tool(self, config_path: str, server_name: str, tool_name: str, **kwargs) -> str:
        """Call a specific tool on a specific MCP server."""
        if not self.stub:
            raise RuntimeError("Not connected to daemon")
            
        request = mcp_daemon_pb2.CallToolRequest(
            config_path=config_path,
            server_name=server_name,
            tool_name=tool_name,
            arguments=json.dumps(kwargs)
        )
        
        response = await self.stub.CallTool(request)
        
        if not response.success:
            raise RuntimeError(f"Tool call failed: {response.error}")
            
        return response.result


class DaemonManager:
    """Manages the daemon lifecycle - starting, stopping, and detecting if it's running."""
    
    @staticmethod
    def is_daemon_running() -> bool:
        """Check if the daemon is currently running."""
        pidfile_path = Path(DEFAULT_PIDFILE)
        
        if not pidfile_path.exists():
            return False
            
        try:
            with open(pidfile_path, 'r') as f:
                pid = int(f.read().strip())
                
            # Check if process with this PID exists
            try:
                os.kill(pid, 0)  # Signal 0 just checks if process exists
                return True
            except OSError:
                # Process doesn't exist, remove stale PID file
                pidfile_path.unlink()
                return False
                
        except (ValueError, FileNotFoundError):
            return False

    @staticmethod
    def start_daemon() -> bool:
        """Start the daemon if it's not already running."""
        if DaemonManager.is_daemon_running():
            logger.debug("Daemon is already running")
            return True
            
        logger.info("Starting MCP daemon...")
        
        try:
            # Find the daemon script
            daemon_script = Path(__file__).parent / "mcp_daemon.py"
            if not daemon_script.exists():
                logger.error(f"Daemon script not found: {daemon_script}")
                return False
                
            # Start daemon in background
            subprocess.Popen([
                sys.executable, str(daemon_script), "--daemon"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for daemon to start
            start_time = time.time()
            while time.time() - start_time < DAEMON_STARTUP_TIMEOUT:
                if DaemonManager.is_daemon_running():
                    # Give it a moment to fully initialize
                    time.sleep(0.5)
                    logger.info("Daemon started successfully")
                    return True
                time.sleep(0.1)
                
            logger.error("Daemon failed to start within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start daemon: {e}")
            return False

    @staticmethod
    def stop_daemon() -> bool:
        """Stop the daemon if it's running."""
        pidfile_path = Path(DEFAULT_PIDFILE)
        
        if not pidfile_path.exists():
            logger.info("Daemon is not running (no PID file)")
            return True
            
        try:
            with open(pidfile_path, 'r') as f:
                pid = int(f.read().strip())
                
            # Send SIGTERM to gracefully stop the daemon
            os.kill(pid, 15)  # SIGTERM
            
            # Wait for process to exit
            start_time = time.time()
            while time.time() - start_time < 10:  # 10 second timeout
                try:
                    os.kill(pid, 0)  # Check if process still exists
                    time.sleep(0.1)
                except OSError:
                    # Process no longer exists
                    logger.info("Daemon stopped successfully")
                    return True
                    
            # If still running, force kill
            logger.warning("Daemon didn't stop gracefully, forcing termination")
            os.kill(pid, 9)  # SIGKILL
            return True
            
        except (ValueError, FileNotFoundError, OSError) as e:
            logger.warning(f"Error stopping daemon: {e}")
            # Clean up PID file anyway
            if pidfile_path.exists():
                pidfile_path.unlink()
            return True


class McpClientManager:
    """High-level manager that handles daemon lifecycle and provides MCP functionality."""
    
    def __init__(self, config_path: str, auto_start_daemon: bool = True):
        self.config_path = config_path
        self.auto_start_daemon = auto_start_daemon
        self.client = McpDaemonClient()

    async def ensure_daemon_running(self) -> bool:
        """Ensure the daemon is running, starting it if necessary."""
        if self.auto_start_daemon and not DaemonManager.is_daemon_running():
            if not DaemonManager.start_daemon():
                return False
        
        # Try to connect to daemon
        return await self.client.connect()

    async def get_all_tools(self) -> Dict[str, List[dict]]:
        """Get all tools from all MCP servers."""
        if not await self.ensure_daemon_running():
            raise RuntimeError("Failed to connect to daemon")
            
        return await self.client.get_all_tools(self.config_path)

    async def call_tool(self, server_name: str, tool_name: str, **kwargs) -> str:
        """Call a specific tool on a specific MCP server."""
        if not await self.ensure_daemon_running():
            raise RuntimeError("Failed to connect to daemon")
            
        return await self.client.call_tool(self.config_path, server_name, tool_name, **kwargs)

    async def cleanup(self):
        """Clean up resources."""
        await self.client.disconnect()


# CLI interface for daemon management
async def main():
    """CLI interface for daemon management."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MCP Daemon Client')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start the daemon')
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop the daemon')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check daemon status')
    
    # Health command
    health_parser = subparsers.add_parser('health', help='Check daemon health')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        success = DaemonManager.start_daemon()
        print("Daemon started successfully" if success else "Failed to start daemon")
        sys.exit(0 if success else 1)
        
    elif args.command == 'stop':
        success = DaemonManager.stop_daemon()
        print("Daemon stopped successfully" if success else "Failed to stop daemon")
        sys.exit(0 if success else 1)
        
    elif args.command == 'status':
        running = DaemonManager.is_daemon_running()
        print("Daemon is running" if running else "Daemon is not running")
        sys.exit(0 if running else 1)
        
    elif args.command == 'health':
        client = McpDaemonClient()
        try:
            if await client.connect():
                healthy = await client.health_check()
                print("Daemon is healthy" if healthy else "Daemon is not healthy")
                sys.exit(0 if healthy else 1)
            else:
                print("Failed to connect to daemon")
                sys.exit(1)
        finally:
            await client.disconnect()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())