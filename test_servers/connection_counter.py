#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["mcp[server]>=1.9.1"]
# ///

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test MCP server counting connections")
    parser.add_argument("--output", required=True, help="File to write JSON events")
    parser.add_argument(
        "--tool-description", required=True, help="Description for the dummy tool"
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        try:
            events = json.loads(output_path.read_text())
        except Exception:
            events = []
    else:
        events = []

    disconnected = False

    def log_event(event: str) -> None:
        events.append({"event": event, "tool_description": args.tool_description})
        output_path.write_text(json.dumps(events))

    def disconnect() -> None:
        nonlocal disconnected
        if not disconnected:
            log_event("disconnect")
            disconnected = True

    signal.signal(signal.SIGTERM, lambda _s, _f: (disconnect(), sys.exit(0)))
    signal.signal(signal.SIGINT, lambda _s, _f: (disconnect(), sys.exit(0)))

    mcp = FastMCP("counter")

    @mcp.tool(name="dummy", description=args.tool_description)
    async def dummy() -> str:
        return "ok"

    log_event("connect")
    try:
        await mcp.run_stdio_async()
    finally:
        disconnect()


if __name__ == "__main__":
    asyncio.run(main())
