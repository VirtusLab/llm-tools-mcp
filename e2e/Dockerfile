# syntax=docker/dockerfile:1.5

FROM ghcr.io/astral-sh/uv:0.7.13 as uv-base

FROM node:24-slim

RUN apt-get update && apt-get install -y python3

COPY --from=uv-base /uv /usr/local/bin/uv

# - uv tools are installed in /root/.local/bin
ENV PATH="/usr/local/bin:/root/.local/bin:$PATH"

WORKDIR /workspace

CMD ["bash"]
