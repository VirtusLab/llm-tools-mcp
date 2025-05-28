#!/bin/bash 

set -uo pipefail  

echo "--------------------------------"
echo "Running mypy..."
uv run pytest
