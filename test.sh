#!/bin/bash

set -uo pipefail

echo "--------------------------------"
echo "Running tests..."
uv run --extra test pytest
