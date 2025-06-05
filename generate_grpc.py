#!/usr/bin/env python3
"""Generate gRPC protobuf files from the proto definition."""

import subprocess
import sys
from pathlib import Path


def generate_grpc_files():
    """Generate gRPC files from proto definition."""
    proto_dir = Path("proto")
    proto_file = proto_dir / "mcp_daemon.proto"
    
    if not proto_file.exists():
        print(f"Error: Proto file not found: {proto_file}")
        return False
    
    # Generate Python gRPC files
    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        "--python_out=.",
        "--grpc_python_out=.",
        f"--proto_path={proto_dir}",
        str(proto_file)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Successfully generated gRPC files:")
        print("- mcp_daemon_pb2.py")
        print("- mcp_daemon_pb2_grpc.py")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error generating gRPC files: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: grpcio-tools not found. Please install it with: pip install grpcio-tools")
        return False


if __name__ == "__main__":
    success = generate_grpc_files()
    sys.exit(0 if success else 1)