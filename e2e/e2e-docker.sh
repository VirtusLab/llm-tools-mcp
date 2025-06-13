#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

docker build -t llm-e2e:latest "$SCRIPT_DIR"

if [[ "${1-}" == "bash" || "${1-}" == "shell" ]]; then
  echo "Running interactive bash shell..."
  docker run --rm -it \
    -v "$SCRIPT_DIR/..:/workspace" \
    -w /workspace \
    llm-e2e:latest bash
else
  echo "Running e2e script..."
  docker run --rm \
    -v "$SCRIPT_DIR/..:/workspace" \
    -w /workspace \
    llm-e2e:latest bash /workspace/e2e/e2e.sh
fi
