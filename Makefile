.PHONY: help setup grpc clean test lint install daemon-start daemon-stop daemon-status

# Default target
help:
	@echo "Available targets:"
	@echo "  setup        - Install dependencies and generate gRPC files"
	@echo "  grpc         - Generate gRPC protobuf files"
	@echo "  clean        - Remove generated files"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linters and type checker"
	@echo "  install      - Install the package in development mode"
	@echo "  daemon-start - Start the MCP daemon"
	@echo "  daemon-stop  - Stop the MCP daemon"
	@echo "  daemon-status- Check daemon status"

# Setup development environment
setup: grpc
	@echo "Development environment setup complete"

# Generate gRPC files
grpc:
	@echo "Generating gRPC protobuf files..."
	python generate_grpc.py

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	rm -f mcp_daemon_pb2.py mcp_daemon_pb2_grpc.py
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run tests
test:
	@echo "Running tests..."
	./test.sh

# Run linters
lint:
	@echo "Running linters and type checker..."
	./check.sh

# Install in development mode
install: grpc
	@echo "Installing in development mode..."
	pip install -e .

# Daemon management targets
daemon-start:
	@echo "Starting MCP daemon..."
	python mcp_client.py start

daemon-stop:
	@echo "Stopping MCP daemon..."
	python mcp_client.py stop

daemon-status:
	@echo "Checking daemon status..."
	python mcp_client.py status