#!/usr/bin/env python3
"""Setup script for llm-tools-mcp with gRPC support."""

import subprocess
import sys
from pathlib import Path

def generate_grpc_files():
    """Generate gRPC files before installation."""
    print("Generating gRPC protobuf files...")
    
    try:
        import grpc_tools.protoc
    except ImportError:
        print("Installing grpcio-tools...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "grpcio-tools"])
    
    # Run the generation script
    result = subprocess.run([sys.executable, "generate_grpc.py"], cwd=Path(__file__).parent)
    if result.returncode != 0:
        print("Failed to generate gRPC files")
        sys.exit(1)
    
    print("gRPC files generated successfully")

def main():
    """Main setup function."""
    # Generate gRPC files first
    generate_grpc_files()
    
    print("Setup completed successfully!")
    print("\nTo use the new client-daemon architecture:")
    print("1. Configure your MCP servers in ~/.llm-tools-mcp/mcp.json")
    print("2. The daemon will be started automatically when using LLM tools")
    print("3. You can manually manage the daemon with:")
    print("   - python mcp_client.py start   # Start daemon")
    print("   - python mcp_client.py stop    # Stop daemon")
    print("   - python mcp_client.py status  # Check status")
    print("   - python mcp_client.py health  # Check health")

if __name__ == "__main__":
    main()