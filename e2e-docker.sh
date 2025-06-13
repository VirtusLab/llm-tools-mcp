#!/bin/bash
set -euo pipefail

# This script runs e2e.sh inside a Docker container so the host
# environment is not affected. Docker must be installed locally.

IMAGE="python:3.11-slim"
CONTAINER_WORKDIR="/work"

# Pass through the UID and GID so created files belong to the host user
USER_ID=$(id -u)
GROUP_ID=$(id -g)

docker run --rm \
  -u ${USER_ID}:${GROUP_ID} \
  -v "$(pwd)":${CONTAINER_WORKDIR} \
  -w ${CONTAINER_WORKDIR} \
  ${IMAGE} bash -c "\
    # Install Node.js so e2e.sh can run the MCP server using npx
    apt-get update && apt-get install -y nodejs npm && \
    pip install --no-cache-dir uv && \
    ./e2e.sh"
